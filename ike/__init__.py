from __future__ import annotations

import ast
import inspect
import textwrap
from ast import BinOp, Expr

import opcode


def byc(func: type(byc)) -> type(byc):
    # TODO: Parse `func.__code__` instead of it's source. (status: lazy)

    # XXX: Python < 3.6 has variable-size opcodes and will 100% fail here.
    #      This code assumes we are not in a six-year-old python.

    body = ast.parse(textwrap.dedent(inspect.getsource(func))).body[0].body
    bytecode = bytearray()
    names = []
    consts = []
    vars = list(func.__code__.co_varnames)
    freevars = func.__code__.co_freevars
    labels = {}
    bcount = 0
    for node in body:
        if type(node) is Expr:
            node = node.value
            if type(node) is BinOp and type(node.op) is ast.LShift:
                labels[node.right.id] = bcount
                node = node.left
            if type(node) is BinOp and type(node.op) is ast.MatMult:
                op = opcode.opmap[node.left.id]
                if op in opcode.hasconst:
                    if type(node.right) is not ast.Constant:
                        node.right = ast.Constant(
                            eval(
                                compile(
                                    ast.Expression(node.right),
                                    func.__code__.co_filename,
                                    "eval",
                                ),
                                func.__globals__,
                                {},
                            ),
                        )
                    if node.right.value not in consts:
                        consts.append(node.right.value)
                elif op in opcode.hasname:
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
            if type(node) is BinOp and type(node.op) is ast.LShift:
                node = node.left
            if type(node) is BinOp and type(node.op) is ast.MatMult:
                op = opcode.opmap[node.left.id]
                bytecode.append(op)
                if op in opcode.hasconst:
                    bytecode.append(consts.index(node.right.value))
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
                    bytecode.append(node.right.value)
            elif type(node) is ast.BinOp and type(node.op) is ast.Mod:
                op = opcode.opmap[node.left.id]
                bytecode.append(op)
                bytecode.append(
                    eval(
                        compile(
                            ast.Expression(node.right),
                            func.__code__.co_filename,
                            "eval"
                        ),
                        func.__globals__,
                        {}
                    )
                )
            elif type(node) is ast.Name:
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

    func.__code__ = (lambda: 0 / 0).__code__.__class__(
        func.__code__.co_argcount,
        func.__code__.co_posonlyargcount,
        func.__code__.co_kwonlyargcount,
        len(vars),
        stack_size,
        flags,
        bytes(bytecode),
        tuple(consts),
        tuple(names),
        vars,
        func.__code__.co_filename,
        func.__code__.co_name,
        func.__code__.co_firstlineno,
        bytes(),  # TODO: actually do this
        freevars,
    )
    return func
