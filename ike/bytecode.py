from __future__ import annotations

import ast
import inspect
import sys
import textwrap
from ast import (Assign, AugAssign, BinOp, Constant, Expr, LShift, MatMult,
                 Mod, Module, Name)
from collections import ChainMap

import opcode

code = (lambda: 0 / 0).__code__.__class__


def byc(func: type(byc)) -> type(byc):
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

    opcode.hasjabs
        A label is expected.

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

    frame = sys._getframe().f_back  # hopefully(!) always the caller's frame
    co = func.__code__
    arg_count = co.co_argcount + co.co_posonlyargcount + co.co_kwonlyargcount

    body = ast.parse(textwrap.dedent(inspect.getsource(func))).body[0].body
    bytecode = bytearray()
    names = []
    consts = []
    vars = list(co.co_varnames[:arg_count])
    freevars = co.co_freevars
    labels = {}
    bcount = 0
    for node in body:
        if type(node) is Expr:
            node = node.value
            if type(node) is BinOp and type(node.op) is LShift:
                labels[node.right.id] = bcount
                node = node.left
            if type(node) is BinOp and type(node.op) is MatMult:
                op = opcode.opmap[node.left.id]
                if op in opcode.hasconst:
                    if type(node.right) is not Constant:
                        node.right = ast.Constant(
                            eval(
                                compile(
                                    ast.Expression(node.right),
                                    co.co_filename,
                                    "eval",
                                ),
                                func.__globals__,
                                frame.f_locals,
                            ),
                        )
                    for v in consts:
                        if object.__eq__(node.right.value, v) is True:
                            break
                    else:
                        consts.append(node.right.value)
                elif op in opcode.hasname:
                    if type(node.right) is Constant:
                        node.right = ast.Name(node.right.value)
                    if node.right.id not in names:
                        names.append(node.right.id)
                elif op in opcode.haslocal:
                    if node.right.id not in vars:
                        vars.append(node.right.id)
            bcount += 1
    names = tuple(names)
    consts = tuple(consts)
    vars = tuple(vars)
    for node in body:
        if type(node) is Expr:
            node = node.value
            if type(node) is BinOp and type(node.op) is LShift:
                node = node.left
            if type(node) is BinOp and type(node.op) is MatMult:
                op = opcode.opmap[node.left.id]
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
                    bytecode.append(
                        eval(
                            compile(
                                ast.Expression(node.right),
                                co.co_filename,
                                "eval",
                            ),
                            func.__globals__,
                            frame.f_locals,
                        )
                    )
            elif type(node) is BinOp and type(node.op) is Mod:
                op = opcode.opmap[node.left.id]
                bytecode.append(op)
                bytecode.append(
                    eval(
                        compile(
                            ast.Expression(node.right),
                            co.co_filename,
                            "eval",
                        ),
                        func.__globals__,
                        frame.f_locals,
                    )
                )
            elif type(node) is Name:
                bytecode.extend((opcode.opmap[node.id], 0))

    stack_size = 0
    current_effect = 0
    for i in range(0, len(bytecode), 2):
        op, arg = bytecode[i : i + 2]
        if op < opcode.HAVE_ARGUMENT:
            arg = None
        current_effect += opcode.stack_effect(op, arg)
        if current_effect > stack_size:
            stack_size = current_effect

    ops = bytecode[::2]
    flags = inspect.CO_NOFREE  # XXX: do these occur in functions?
    og_flags = func.__code__.co_flags
    if set(opcode.hasfree).intersection(ops):
        flags |= inspect.CO_OPTIMIZED

    flags |= og_flags & inspect.CO_COROUTINE
    if opcode.opmap["YIELD_VALUE"] in ops or opcode.opmap["YIELD_FROM"] in ops:
        flags |= inspect.CO_GENERATOR

    if flags & inspect.CO_COROUTINE and flags & inspect.CO_GENERATOR:
        flags ^= inspect.CO_COROUTINE | inspect.CO_GENERATOR
        flags |= inspect.CO_ASYNC_GENERATOR

    if vars:
        flags |= inspect.CO_NEWLOCALS

    flags |= og_flags & inspect.CO_VARARGS
    flags |= og_flags & inspect.CO_VARKEYWORDS
    flags |= og_flags & inspect.CO_NESTED

    opts = {
        "FLAGS": flags,
        "STACK_SIZE": stack_size,
        "NAMES": names,
        "CONSTS": consts,
        "VARNAMES": vars,
        "FREEVARS": freevars,
    }
    for node in body:
        if type(node) is Assign or type(node) is AugAssign:
            exec(
                compile(
                    Module([node], []),
                    co.co_filename,
                    "exec",
                ),
                {},
                ChainMap(opts, frame.f_locals),
            )

    flags = opts["FLAGS"]
    stack_size = opts["STACK_SIZE"]
    names = opts["NAMES"]
    consts = opts["CONSTS"]
    vars = opts["VARNAMES"]
    freevars = opts["FREEVARS"]

    func.__code__ = code(
        co.co_argcount,
        co.co_posonlyargcount,
        co.co_kwonlyargcount,
        len(vars),
        stack_size,
        flags,
        bytes(bytecode),
        consts,
        names,
        vars,
        co.co_filename,
        co.co_name,
        co.co_firstlineno,
        bytes(),  # TODO: actually do this
        freevars,
    )
    return func