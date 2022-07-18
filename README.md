# ike: _awful functions for everything you shouldn't do_

ever saw python bytecode and thought "I can do better"? want to read objects in memory as-is? ..no??? me neither!

**BUT NOW YOU CAN!!**

```py
@ike.byc
def sqrt(n: float) -> float:
    LOAD_FAST @ n
    LOAD_CONST @ .5
    INPLACE_POWER
    RETURN_VALUE

print(f"{sqrt(2) = }")  # = 1.4142135623730951
```

## WHAT

I DONT KNOW EITHER oK

## Install

This package is not (yet?) available on PyPI.

```sh
pip install git+https://github.com/dzshn/ike
# or `py -m pip` etc
```

<br> <br> <br>

i am sorry. please direct complaints to [me](https://dzshn.xyz)
