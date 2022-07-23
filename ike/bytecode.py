"""Bytecode manipulation and crafting functions."""
from __future__ import annotations

import inspect
import sys
import textwrap
import warnings
from ast import (Assign, AugAssign, BinOp, Constant, Expr, Expression, LShift,
                 MatMult, Mod, Module, Name, PyCF_ONLY_AST)
from collections import ChainMap
from collections.abc import Callable

import opcode
from opcode import opmap

code = (lambda: 0 / 0).__code__.__class__
_hasjump = opcode.hasjabs + opcode.hasjrel


class UnsafeBytecode(RuntimeWarning):
    """Unsafe bytecode was found.

    Usually, this means the code is prone to crashing the interpreter
    unpredictably (usually with a segfault). Do not ignore this warning unless
    you know what you're doing, even if seems to work.
    """

    pass


warnings.filterwarnings("error", category=UnsafeBytecode)


def guess_flags(bytecode: bytes, original_flags: int = 0) -> int:
    """Guess the suited flags for a given bytecode.

    This function assumes the bytecode is for a function.

    Parameters
    ----------
    bytecode : bytes
    original_flags : int, optional
        If provided, ``VARARGS``, ``VARKEYWORDS``, ``NESTED`` and
        ``COROUTINE`` will be copied from it. This is useful if
        patching a function.

    Returns
    -------
    int
    """
    flags = inspect.CO_NOFREE
    for op in bytecode[::2]:
        if op in opcode.hasfree and flags & inspect.CO_NOFREE:
            flags ^= inspect.CO_NOFREE
        if op == opmap["YIELD_VALUE"] or op == opmap["YIELD_FROM"]:
            flags |= inspect.CO_GENERATOR
        if op == opmap["STORE_FAST"]:
            flags |= inspect.CO_NEWLOCALS

    flags |= original_flags & (
        inspect.CO_VARARGS
        | inspect.CO_VARKEYWORDS
        | inspect.CO_NESTED
        | inspect.CO_COROUTINE
    )

    if flags & (inspect.CO_COROUTINE & inspect.CO_GENERATOR):
        flags ^= inspect.CO_COROUTINE | inspect.CO_GENERATOR
        flags |= inspect.CO_ASYNC_GENERATOR

    return flags


def stackdepth(bytecode: bytes) -> int:
    """Calculate the stack depth for a given bytecode.

    Parameters
    ----------
    bytecode : bytes

    Returns
    -------
    int

    Warns
    -----
    UnsafeBytecode
        One of the flow paths has not balanced out it's stack before jumping,
        or has reached a negative length at any point.
    """
    stacksize = 0
    current = 0
    for i, (op, arg) in enumerate(zip(*[iter(bytecode)] * 2)):
        if op < opcode.HAVE_ARGUMENT:
            current += opcode.stack_effect(op)
        else:
            current += opcode.stack_effect(op, arg)
        if current > stacksize:
            stacksize = current

        if current < 0:
            warnings.warn(
                "Bad stack: possible pop from empty stack: [%d] %s %s"
                % (i, opcode.opname[op], arg),
                UnsafeBytecode,
                stacklevel=3,
            )
        if op in _hasjump:
            if current != 0:
                warnings.warn(
                    "Bad stack: non-zero stack effect before jump: [%d] %s %s"
                    % (i, opcode.opname[op], arg),
                    UnsafeBytecode,
                    stacklevel=3,
                )
            target = arg
            if op in opcode.hasjrel:
                target += i

            branch_effect = current
            for j, (op, arg) in enumerate(zip(*[iter(bytecode[target * 2 :])] * 2)):
                if op < opcode.HAVE_ARGUMENT:
                    branch_effect += opcode.stack_effect(op)
                else:
                    branch_effect += opcode.stack_effect(op, arg)
                if branch_effect < 0:
                    warnings.warn(
                        "Bad stack: possible pop from empty stack: [%d->%d] %s %s"
                        % (i, j, opcode.opname[op], arg),
                        UnsafeBytecode,
                        stacklevel=3,
                    )
                if op in _hasjump and branch_effect != 0:
                    warnings.warn(
                        "Bad stack: non-zero stack effect before jump: [%d->%d] %s %s"
                        % (i, j, opcode.opname[op], arg),
                        UnsafeBytecode,
                        stacklevel=3,
                    )

    return stacksize


def _build_linetable(lines):
    table = [(-1, -1, -1)]
    for line, offset in lines:
        ps, pe, pl = table[-1]
        if pl == line:
            table[-1] = (ps, offset + 2, pl)
        else:
            table.append((offset, offset + 2, line))
    table.pop(0)
    deltas = bytearray()
    line = 0
    for a, b, c in table:
        db, dl = b - a, c - line
        if not (0 <= db <= 254 and 0 <= dl <= 127):
            # This is your fate for putting 252 opcodes in one line
            return bytes()
        deltas.extend((db, dl))
        line = c
    return bytes(deltas)


def byc(func: Callable) -> Callable:
    """Induce a headache on the function caller.

    Specification::
        body          ::= (instruction | option)*
        instruction   ::= opcode ["@" | "%" argument] ["<<" label]
        opcode        ::= <Any identifier present in ``opcode.opmap``>
        argument      ::= <Any valid expression>
        raw_argument  ::= <Any expression resulting in an int>
        label         ::= <Any valid identifier>
        option        ::= <Any assignment>

    You may assign values to FLAGS, STACK_SIZE, NAMES, CONSTS, VARNAMES,
    FREEVARS as necessary. These are created automatically for you but some
    extra evilness is possible with this.

    If the argument is not provided, it is regarded as 0. If provided using
    ``%``, it is used as-is. ``@`` expects the following rules:

    opcode.hascompare
        A string in `opcode.cmp_op` is expected and converted to it's index.

    opcode.hasconst
        If the value is not yet in `co_consts`, it will be appended to it.

    opcode.hasfree, opcode.haslocal, opcode.hasname
        Either an identifier or a string is expected and appended to the
        corresponding tuple (e.g. `co_varnames` for a `LOAD_FAST`).

    opcode.hasjabs, opcode.hasjrel
        A label is expected.

    Warns
    -----
    UnsafeBytecode
        Most likely you don't want to run the generated function.

    Warnings
    --------
    This allows you to work at a quite low level of Python's interpreter, keep
    in mind that ANY errors you commit may result in a irrecoverable crash.

    Notes
    -----
    This won't work in the builtin REPL because the function source code can't
    be introspected. You can instead use IPython or write a script.

    See Also
    --------
    dis, inspect

    Examples
    --------
    >>> @ike.byc
    ... def sqrt(n: float) -> float:
    ...     LOAD_FAST @ n
    ...     LOAD_CONST @ .5
    ...     INPLACE_POWER
    ...     RETURN_VALUE
    ...
    >>> sqrt(2)
    1.4142135623730951
    """

    # TODO: Parse `func.__code__` instead of it's source. (status: lazy)

    # XXX: Python < 3.6 has variable-size opcodes and will 100% fail here.
    #      This code assumes we are not in a six-year-old python.

    # got damn fat flow graph ..... cyclomatic complexity of 35 ....

    frame = sys._getframe().f_back  # hopefully(!) always the caller's frame
    co = func.__code__
    arg_count = co.co_argcount + co.co_posonlyargcount + co.co_kwonlyargcount

    def _eval(node, globals=func.__globals__, locals=frame.f_locals):
        return eval(
            compile(Expression(node), co.co_filename, "eval"),
            globals,
            locals,
        )

    def _cast(node, t):
        if type(node) is not t:
            return t(_eval(node))
        return node

    src = textwrap.dedent(inspect.getsource(func))
    body = compile(src, co.co_filename, "exec", PyCF_ONLY_AST).body[0].body
    bytecode = bytearray()
    names = []
    consts = []
    vars = list(co.co_varnames[:arg_count])
    freevars = list(co.co_freevars)
    labels = {}
    bcount = 0
    lines = []
    for node in body:
        if type(node) is not Expr and type(node) is not Name:
            continue

        if type(node) is Expr:
            node = node.value
        if type(node) is BinOp and type(node.op) is LShift:
            node.right = _cast(node.right, Name)
            labels[node.right.id] = bcount
            node = node.left
        if type(node) is BinOp and type(node.op) is MatMult:
            op = opcode.opmap[node.left.id]
            if op in opcode.hasconst:
                node.right = _cast(node.right, Constant)
                for v in consts:
                    if object.__eq__(node.right.value, v) is True:
                        break
                else:
                    consts.append(node.right.value)
            elif op in opcode.hasfree + opcode.haslocal + opcode.hasname:
                if op in opcode.hasname:
                    scope = names
                elif op in opcode.haslocal:
                    scope = vars
                elif op in opcode.hasfree:
                    scope = freevars

                node.right = _cast(node.right, Name)
                if node.right.id not in scope:
                    scope.append(node.right.id)
        elif type(node) is BinOp and type(node.op) is not Mod:
            continue
        elif type(node) is not Name:
            continue

        lines.append((node.lineno - 1, bcount))
        bcount += 1

    names = tuple(names)
    consts = tuple(consts)
    vars = tuple(vars)
    freevars = tuple(freevars)
    for node in body:
        if type(node) is Expr:
            node = node.value
            if type(node) is BinOp and type(node.op) is LShift:
                node = node.left
            if type(node) is BinOp and type(node.op) is MatMult:
                op = opmap[node.left.id]
                bytecode.append(op)
                if op in opcode.hasconst:
                    for i, v in enumerate(consts):
                        if object.__eq__(node.right.value, v) is True:
                            bytecode.append(i)
                            break
                elif op in opcode.hasname:
                    bytecode.append(names.index(node.right.id))
                elif op in opcode.haslocal:
                    bytecode.append(vars.index(node.right.id))
                elif op in opcode.hasfree:
                    bytecode.append(freevars.index(node.right.id))
                elif op in opcode.hascompare:
                    bytecode.append(opcode.cmp_op.index(node.right.value))
                elif op in opcode.hasjabs:
                    bytecode.append(labels[node.right.id])
                else:
                    bytecode.append(_eval(node.right))
            elif type(node) is BinOp and type(node.op) is Mod:
                op = opcode.opmap[node.left.id]
                bytecode.append(op)
                bytecode.append(_eval(node.right))
            elif type(node) is Name:
                bytecode.extend((opcode.opmap[node.id], 0))

    stacksize = stackdepth(bytecode)
    flags = guess_flags(bytecode, co.co_flags)
    linetable = _build_linetable(lines)

    opts = {
        "FLAGS": flags,
        "STACK_SIZE": stacksize,
        "NAMES": names,
        "CONSTS": consts,
        "VARNAMES": vars,
        "FREEVARS": freevars,
    }
    for node in body:
        if type(node) is Assign or type(node) is AugAssign:
            exec(
                compile(Module([node], []), co.co_filename, "exec"),
                func.__globals__,
                ChainMap(opts, frame.f_locals),
            )

    flags = opts["FLAGS"]
    stacksize = opts["STACK_SIZE"]
    names = opts["NAMES"]
    consts = opts["CONSTS"]
    vars = opts["VARNAMES"]
    freevars = opts["FREEVARS"]

    func.__code__ = code(
        co.co_argcount,
        co.co_posonlyargcount,
        co.co_kwonlyargcount,
        len(vars),
        stacksize,
        flags,
        bytes(bytecode),
        consts,
        names,
        vars,
        co.co_filename,
        co.co_name,
        co.co_firstlineno,
        linetable,
        freevars,
        (),  # how tj do i deal with ``cellvars``
    )
    return func
