import copy
import ctypes
import math
import struct
import sys
from typing import Union

import mem_edit

from app.helpers.aob_value import AOBValue
from app.helpers.exceptions import ValueException, AOBException

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class Value:
    def __init__(self, value:str, store_size=1):
        self.raw_value = value
        self.store_size = store_size
        self.bytes = bytes(0)

    def get(self):
        return None

    def from_bytes(self, _bytes):
        return 0

    def to_bytes(self):
        return bytes([0])

    def get_store_size(self):
        return self.store_size

    def get_store_type(self):
        return None

    def is_signed(self):
        return False

    def get_printable(self):
        return self.get()

    def get_comparable_value(self):
        return self.get()

    def get_ctype(self):
        return ctypes.c_byte

    def cast(self, obj):
        return None

    def read_memory(self, memory: mem_edit.Process, address: int):
        return None

    def read_bytes_from_memory(self, memory: mem_edit.Process, address: int):
        return bytes([0])

    def write_bytes_to_memory(self, memory: mem_edit.Process, address: int):
        pass

    def compare_memory(self, memory: mem_edit.Process, address: int):
        return -1

    @staticmethod
    def create(_value:str, _size:str, _signed=None):
        valid_sizes = ['byte_1', 'byte_2', 'byte_4', 'byte_8', 'array', 'float', 'address', 'offset']
        _size = _size.strip()
        _value = _value.strip()
        if _size not in valid_sizes:
            raise ValueException("{} is not a valid size".format(_size))
        if _size == 'byte_1':
            return IntValue(_value, store_size=1, _signed=_signed)
        if _size == 'byte_2':
            return IntValue(_value, store_size=2, _signed=_signed)
        if _size == 'byte_4':
            return IntValue(_value, store_size=4, _signed=_signed)
        if _size == 'byte_8':
            return IntValue(_value, store_size=8, _signed=_signed)
        if _size == 'float':
            return FloatValue(_value)
        if _size == 'address':
            return Address(_value)
        if _size == 'offset':
            return Offset(_value)
        if _size == 'array':
            return AOB(_value)

    @staticmethod
    def is_float(val: str):
        try:
            float(val)
        except ValueError:
            return False
        return True

    @staticmethod
    def is_int(val: str):
        try:
            int(val)
        except ValueError:
            return False
        return True

    def copy(self, _signed=None):
        if isinstance(self, IntValue) and _signed is not None:
            return IntValue(str(self.get()), self.store_size, _signed)
        return copy.deepcopy(self)




class FloatValue(Value):
    round_digits = 3
    def __init__(self, value: str):
        super().__init__(value, store_size=4)
        try:
            self.value = float(self.raw_value)
            self.bytes = bytes(ctypes.c_float(self.value))
        except ValueError:
            raise ValueException("{} is not a valid float value".format(self.raw_value))
        
    def __lt__(self, other):
        return round(self.value, self.round_digits) < round(other.value, self.round_digits)
    
    def __le__(self, other):
        return round(self.value, self.round_digits) <= round(other.value, self.round_digits)
    
    def __gt__(self, other):
        return round(self.value, self.round_digits) > round(other.value, self.round_digits)
    
    def __ge__(self, other):
        return round(self.value, self.round_digits) >= round(other.value, self.round_digits)
    
    def __eq__(self, other):
        return round(self.value, self.round_digits) == round(other.value, self.round_digits)
    
    def __ne__(self, other):
        return round(self.value, self.round_digits) != round(other.value, self.round_digits)

    def get(self):
        return self.value

    def get_ctype(self):
        return ctypes.c_byte

    def cast(self, obj):
        return ctypes.cast(obj, ctypes.POINTER(ctypes.c_float))

    def get_store_type(self):
        return "float"

    def from_bytes(self, _bytes:bytes):
        if len(_bytes) != 4:
            ba = bytearray(_bytes)
            ba.extend([0] * (4 - len(_bytes)))
            _bytes = bytes(ba)
        return struct.unpack("f", _bytes)[0]

    def to_bytes(self):
        return struct.pack("f", self.get())

    def get_comparable_value(self):
        return round(self.value, self.round_digits)

    def read_memory(self, memory: mem_edit.Process, address: int):
        read = memory.read_memory(address, ctypes.c_float())
        self.value = read.value
        self.bytes = bytes(read)
        self.raw_value = str(self.value)

    def read_bytes_from_memory(self, memory: mem_edit.Process, address: int):
        return bytes(memory.read_memory(address, ctypes.c_float()))

    def write_bytes_to_memory(self, memory: mem_edit.Process, address: int):
        memory.write_memory(address, ctypes.c_float(self.value))

    def compare_memory(self, memory: mem_edit.Process, address: int):
        try:
            read = memory.read_memory(address, ctypes.c_float()).value
            if math.isclose(read, self.value, abs_tol=0.001):
                return 0
            return 1 if read < self.value else -1
        except OSError:
            return -1

class IntValue(Value):
    def __init__(self, value: str, store_size, _signed = None):
        super().__init__(value, store_size=store_size)
        try:
            if not Value.is_int(self.raw_value) and Value.is_float(self.raw_value):
                self.raw_value = int(float(self.raw_value))
            self.value = int(self.raw_value)
            if store_size == 1:
                self.bytes = bytes(ctypes.c_int8(self.value))
                self.signed = self.value < (2 << 6) if _signed is None else _signed
            elif store_size == 2:
                self.bytes = bytes(ctypes.c_int16(self.value))
                self.signed = self.value < (2 << 14) if _signed is None else _signed
            elif store_size == 4:
                self.bytes = bytes(ctypes.c_int32(self.value))
                self.signed = self.value < (2 << 30) if _signed is None else _signed
            elif store_size == 8:
                self.bytes = bytes(ctypes.c_int64(self.value))
                self.signed = self.value < (2 << 62) if _signed is None else _signed
            else:
                raise ValueException("{} is not a valid store size".format(self.store_size))
        except ValueError:
            raise ValueException("{} is not a valid int value".format(self.raw_value))

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def is_signed(self):
        return self.signed

    def set_signed(self, _signed):
        self.signed = _signed

    def get_store_type(self):
        if self.store_size == 1:
            return "byte_1"
        elif self.store_size == 2:
            return "byte_2"
        elif self.store_size == 8:
            return "byte_8"
        else:
            return "byte_4"

    def get(self):
        return self.value

    def get_ctype(self):
        return ctypes.c_byte if self.signed else ctypes.c_ubyte

    def cast(self, obj):
        if self.store_size == 1:
            return ctypes.cast(obj, ctypes.POINTER(ctypes.c_int8)) if self.signed else ctypes.cast(obj, ctypes.POINTER(ctypes.c_uint8))
        if self.store_size == 2:
            return ctypes.cast(obj, ctypes.POINTER(ctypes.c_int16)) if self.signed else ctypes.cast(obj, ctypes.POINTER(ctypes.c_uint16))
        if self.store_size == 4:
            return ctypes.cast(obj, ctypes.POINTER(ctypes.c_int32)) if self.signed else ctypes.cast(obj, ctypes.POINTER(ctypes.c_uint32))
        if self.store_size == 8:
            return ctypes.cast(obj, ctypes.POINTER(ctypes.c_int64)) if self.signed else ctypes.cast(obj, ctypes.POINTER(ctypes.c_uint64))
        return None



    def read_memory(self, memory: mem_edit.Process, address: int):
        read = memory.read_memory(address, (ctypes.c_byte * self.store_size)())
        self.bytes = bytes(read)
        self.value = int.from_bytes(self.bytes, byteorder=sys.byteorder, signed=self.signed)
        self.raw_value = str(self.value)

    def read_bytes_from_memory(self, memory: mem_edit.Process, address: int):
        return bytes(memory.read_memory(address, (ctypes.c_byte * self.store_size)()))

    def write_bytes_to_memory(self, memory: mem_edit.Process, address: int):
        memory.write_memory(address, (ctypes.c_byte * self.store_size)(*self.bytes))

    def compare_memory(self, memory: mem_edit.Process, address: int):
        try:
            read = memory.read_memory(address, (ctypes.c_byte * self.store_size)())
            _bytes = bytes(read)
            if _bytes == self.bytes:
                return 0
            return 1 if int.from_bytes(_bytes, byteorder=sys.byteorder) < self.value else -1
        except OSError:
            return -1

    def from_bytes(self, _bytes):
        return int.from_bytes(_bytes, byteorder=sys.byteorder, signed=self.signed)

    def to_bytes(self):
        try:
            return self.get().to_bytes(self.store_size, byteorder=sys.byteorder, signed=self.signed)
        except OverflowError:
            return (self.get() & (0x01 << (self.store_size*8)) - 1).to_bytes(self.store_size, byteorder=sys.byteorder, signed=self.signed)



class Address(IntValue):
    def __init__(self, value: str):
        import re
        if not re.match(r'[0-9A-F]{4,16}', value.upper()):
            raise ValueException("{} is not an address".format(value))
        super().__init__(str(int(value, 16)), store_size=4)

    def get_printable(self):
        return '{:X}'.format(self.value)

class Offset(IntValue):
    def __init__(self, value: str, _is_hex=True):
        if _is_hex:
            import re
            if not re.match(r'[0-9A-F]+', value.upper()):
                raise ValueException("{} is not an offset".format(value))
            super().__init__(str(int(value, 16)), store_size=4)
        else:
            super().__init__(value, store_size=4)
        self._is_hex = _is_hex

    def get_printable(self):
        if self._is_hex:
            return '{:X}'.format(self.value)
        return self.value

    def is_hex(self):
        return self._is_hex

class AOB(Value):
    def __init__(self, value: str):
        try:
            self.value = AOBValue(value)
            super().__init__(value, store_size=len(self.value.aob_item['aob_array']))
        except AOBException:
            raise ValueException("{} is not a valid AOB value".format(self.raw_value))

    def __lt__(self, other):
        raise ValueException("Cannot compare AOBs")

    def __le__(self, other):
        raise ValueException("Cannot compare AOBs")

    def __gt__(self, other):
        raise ValueException("Cannot compare AOBs")

    def __ge__(self, other):
        raise ValueException("Cannot compare AOBs")

    def __eq__(self, other):
        return self.value.equal(other)

    def __ne__(self, other):
        return not self.value.equal(other)

    def get(self):
        return self.get_printable()

    def get_store_type(self):
        return "array"

    def from_bytes(self, _bytes):
        return AOBValue.from_bytes(_bytes).aob_item['aob_bytes']

    def read_memory(self, memory: mem_edit.Process, address: int):
        read = memory.read_memory(address, (ctypes.c_byte * self.store_size)())
        self.value = AOBValue.from_bytes(bytes(read))
        self.raw_value = self.value.aob_item['aob_string']
        self.store_size = len(bytes(read))
        self.bytes = bytes(read)

    def read_bytes_from_memory(self, memory: mem_edit.Process, address: int):
        return bytes(memory.read_memory(address, (ctypes.c_byte * self.store_size)()))

    def get_printable(self):
        return self.value.aob_item['aob_string']

    def get_ctype(self):
        return ctypes.c_ubyte


    def compare_memory(self, memory: mem_edit.Process, address: int):
        try:
            read = memory.read_memory(address, (ctypes.c_ubyte * self.store_size)())
            _bytes = bytes(read)
            for i in range(0, len(self.value.aob_item['aob_bytes'])):
                v = self.value.aob_item['aob_bytes'][i]
                if v >= 256:
                    continue
                if v != _bytes[i]:
                    return -1
            return 0
        except OSError:
            return -1

    def to_bytes(self):
        return self.bytes


