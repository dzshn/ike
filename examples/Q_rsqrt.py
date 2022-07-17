import ike


@ike.byc
def Q_rsqrt(n: float) -> float:
    LOAD_CONST @ 0
    LOAD_CONST @ None
    IMPORT_NAME @ ctypes
    IMPORT_STAR
    LOAD_FAST @ cast
    LOAD_FAST @ pointer
    LOAD_FAST @ c_long
    LOAD_CONST @ 0x5F3759DF
    LOAD_FAST @ cast
    LOAD_FAST @ pointer
    LOAD_FAST @ c_float
    LOAD_FAST @ n
    CALL_FUNCTION @ 1
    CALL_FUNCTION @ 1
    LOAD_FAST @ POINTER
    LOAD_FAST @ c_long
    CALL_FUNCTION @ 1
    CALL_FUNCTION @ 2
    LOAD_ATTR @ contents
    LOAD_ATTR @ value  # evil floating point bit level hacking
    LOAD_CONST @ 1
    INPLACE_RSHIFT
    INPLACE_SUBTRACT  # what the fuck?
    CALL_FUNCTION @ 1
    CALL_FUNCTION @ 1
    LOAD_FAST @ POINTER
    LOAD_FAST @ c_float
    CALL_FUNCTION @ 1
    CALL_FUNCTION @ 2
    LOAD_ATTR @ contents
    LOAD_ATTR @ value
    STORE_FAST @ y
    LOAD_FAST @ y
    LOAD_CONST @ 1.5
    LOAD_FAST @ n
    LOAD_CONST @ 0.5
    INPLACE_MULTIPLY
    LOAD_FAST @ y
    INPLACE_MULTIPLY
    LOAD_FAST @ y
    INPLACE_MULTIPLY
    INPLACE_SUBTRACT
    INPLACE_MULTIPLY  # 1st iteration
    # STORE_FAST @ y
    # LOAD_FAST @ y
    # LOAD_CONST @ 1.5
    # LOAD_FAST @ n
    # LOAD_CONST @ 0.5
    # INPLACE_MULTIPLY
    # LOAD_FAST @ y
    # INPLACE_MULTIPLY
    # LOAD_FAST @ y
    # INPLACE_MULTIPLY
    # INPLACE_SUBTRACT
    # INPLACE_MULTIPLY  # 2nd iteration, this can be removed
    RETURN_VALUE


print(f"{Q_rsqrt(0.15625) = }")  # = 2.5254863388218056
