import ike
import sys

from collections.abc import Iterator


@ike.byc
def sqrt(n: float) -> float:
    LOAD_FAST @ n
    LOAD_CONST @ 0.5
    INPLACE_POWER
    RETURN_VALUE


@ike.byc
def fib(n: int) -> int:
    LOAD_FAST @ n
    LOAD_CONST @ 2
    COMPARE_OP @ "<"
    POP_JUMP_IF_FALSE @ RECURSE

    LOAD_FAST @ n
    RETURN_VALUE

    LOAD_GLOBAL @ fib << RECURSE
    LOAD_FAST @ n
    LOAD_CONST @ 1
    INPLACE_SUBTRACT
    CALL_FUNCTION @ 1
    LOAD_GLOBAL @ fib
    LOAD_FAST @ n
    LOAD_CONST @ 2
    INPLACE_SUBTRACT
    CALL_FUNCTION @ 1
    INPLACE_ADD
    RETURN_VALUE


@ike.byc
def fib_iter(n: int) -> Iterator[int]:
    LOAD_CONST @ 0; STORE_FAST @ a
    LOAD_CONST @ 1; STORE_FAST @ b

    LOAD_FAST @ a << LOOP
    YIELD_VALUE
    POP_TOP
    LOAD_FAST @ b
    LOAD_FAST @ a
    LOAD_FAST @ b
    INPLACE_ADD
    STORE_FAST @ b
    STORE_FAST @ a
    LOAD_FAST @ n
    LOAD_CONST @ 1
    INPLACE_SUBTRACT
    STORE_FAST @ n
    LOAD_FAST @ n
    POP_JUMP_IF_TRUE @ LOOP

    LOAD_CONST @ None
    RETURN_VALUE


@ike.byc
def hai() -> None:
    LOAD_CONST @ 0
    LOAD_CONST @ None
    IMPORT_NAME @ ctypes
    LOAD_ATTR @ cdll
    LOAD_ATTR @ "libc.so.6"
    LOAD_ATTR @ syscall
    LOAD_CONST @ 1
    LOAD_CONST @ 1
    LOAD_CONST @ 0
    LOAD_CONST @ None
    IMPORT_NAME @ ctypes
    LOAD_ATTR @ c_char_p
    LOAD_CONST @ b"hoi !\n"
    CALL_FUNCTION @ 1
    LOAD_CONST @ 6
    CALL_FUNCTION @ 4

    # POP_TOP
    LOAD_CONST @ None
    RETURN_VALUE


def evil(address: int):
    # Trick `PyTuple_GetItem` into reading an arbitrary `*PyObject` :3
    # check the following for a full exploit
    # <https://github.com/chilaxan/pysnippets/blob/main/native_ctypes/load_addr.py>

    py_ssize_t_size = (None, ).__sizeof__() - tuple.__basicsize__

    consts = ()
    pointer = address.to_bytes(py_ssize_t_size, sys.byteorder)
    offset = (
        # Position of `address` inside `pointer`
        (id(pointer) + bytes.__basicsize__ - 1)
        # Start of `PyTupleObject.ob_item`
        - (id(consts) + tuple.__basicsize__)
    ) // py_ssize_t_size
    # we do a little overflowing
    a, b, c, d, e = offset.to_bytes(5, sys.byteorder, signed=True)

    @ike.byc
    def magic():
        CONSTS = consts
        EXTENDED_ARG % e
        EXTENDED_ARG % d
        EXTENDED_ARG % c
        EXTENDED_ARG % b
        LOAD_CONST % a
        RETURN_VALUE

    return magic()


print(f"{sqrt(2) = }")
print(f"{[fib(i) for i in range(16)] = }")
print(f"{list(fib_iter(16)) = }")
# hai()  # <- try this if you have an unix system
print(f"{evil(id(ike)) = }")
