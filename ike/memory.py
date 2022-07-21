import ctypes


def dump_pyobj(thing: object) -> bytes:
    """Read a ``PyObject``'s raw bytes.

    Parameters
    ----------
    thing : object
        Literally anything.

    Returns
    -------
    bytes
    """
    x = id(thing)
    return bytes(
        ctypes.c_ubyte.from_address(x + i).value
        for i in range(thing.__sizeof__())
    )
