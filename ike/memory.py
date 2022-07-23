"""Functions for peeking and poking memory."""
from ctypes import c_int, c_ssize_t, c_ubyte, c_void_p, py_object, pythonapi


def sizeof(thing: object) -> int:
    """Get the size of an object in memory."""
    for cls in thing.__class__.__mro__:
        if cls.__sizeof__.__class__ is not (lambda: 0 / 0).__class__:
            return cls.__sizeof__(thing)


def peek(addr: int, length: int = 1) -> bytes:
    """Read raw bytes from memory."""
    return bytes((c_ubyte * length).from_address(addr))


def poke(addr: int, data: bytes):
    """Write raw bytes into memory."""
    (c_ubyte * len(data)).from_address(addr)[:] = data


def view(addr: int, length: int) -> memoryview:
    """Return a memoryview pointed to arbitrary memory."""
    fn = pythonapi.PyMemoryView_FromMemory
    fn.restype = py_object
    return fn(c_void_p(addr), c_ssize_t(length), c_int(0x200))


def peeko(thing: object) -> bytes:
    """``peek`` an entire object."""
    return peek(id(thing), sizeof(thing))


def viewo(thing: object) -> memoryview:
    """``view`` an entire object."""
    return view(id(thing), sizeof(thing))
