import ike

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


print(f"{sqrt(2) = }")
print(f"{[fib(i) for i in range(16)] = }")
print(f"{list(fib_iter(16)) = }")
