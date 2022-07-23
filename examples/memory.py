import sys
from ike.memory import peek, poke


def refcnt(thing: object) -> int:
    return int.from_bytes(peek(id(thing), 8), sys.byteorder)


def fix_9plus10():
    poke(id(19) + int.__basicsize__, bytes([21]))
    print(9 + 10)  # 21
