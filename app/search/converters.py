import ctypes

class FloatConvert(ctypes.Union):
    _fields_ = (("bytes", ctypes.c_char * ctypes.sizeof(ctypes.c_float)),
                ("float", ctypes.c_float))

    def to_bytes(self, value: float):
        return bytes(ctypes.c_float(value))


    def from_bytes(self, _bytes: bytes):
        conv = FloatConvert()
        conv.bytes = _bytes
        return conv.float
