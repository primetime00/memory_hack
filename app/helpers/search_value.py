import ctypes
from typing import Union

import app.helpers.memory_utils as memory_utils
from app.helpers.aob_value import AOBValue
from app.helpers.exceptions import SearchException

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class SearchValue:
    def __init__(self, value: str, size: str):
        self.aob: AOBValue = None
        self.cmp = None
        self.cmp_other = None
        self.value = None
        if not value:
            value = "0"
        self.raw_value = value if not value.lower().startswith('0x') else str(int(value, 16))
        self.parse_value(self.raw_value, size)

    def parse_value(self, value: str, size: str):
        value = value.strip()
        if size == 'array': #special case
            self.aob = AOBValue(value)
            self.cmp = self._cmp_aob
        else:
            ctype = memory_utils.get_ctype(value, size)
            if size == 'float':
                self.value = ctype(float(value))
                self.cmp = self._cmp_float
                self.cmp_other = self._cmp_float_other
            else:
                self.value = ctype(int(value))
                self.cmp = self._cmp_int
                self.cmp_other = self._cmp_int_other

    def get_value(self):
        if self.aob:
            return self.aob
        return self.value

    def get_type(self):
        if self.aob:
            return type(self.aob.aob_search_value) * self.aob.aob_item['size']
        return type(self.value)

    def get_raw_value(self):
        return self.raw_value

    def is_aob(self):
        return self.aob is not None

    def get_search_value(self):
        if self.aob:
            return self.aob.get_search_value()
        return self.value

    def get_size(self):
        if self.aob:
            return self.aob.aob_item['size']
        return ctypes.sizeof(self.value)

    def get_offset(self):
        if self.aob:
            return self.aob.get_offset()
        return 0

    def get_byte(self, offset):
        if self.aob:
            return self.aob.aob_item['aob_bytes'][offset]
        return self.value[offset]

    def get_bytes(self):
        if self.aob:
            return self.aob.aob_item['aob_bytes']
        return self.value

    def equals(self, buffer):
        if self.aob:
            bts = self.get_bytes()
            for i in range(0, len(bts)):
                bt = bts[i]
                if bt > 255:
                    continue
                if bt != buffer[i]:
                    return False
            return True
        return self.value.value == buffer.value

    def _cmp_aob(self, buffer):
        raise SearchException("Cannot compare AOBs")

    def _cmp_int(self, buffer):
        if self.value.value > buffer.value:
            return 1
        elif self.value.value < buffer.value:
            return -1
        return 0

    def _cmp_float(self, buffer):
        if round(self.value.value,3) > round(buffer.value,3):
            return 1
        elif round(self.value.value,3) < round(buffer.value,3):
            return -1
        return 0

    def _cmp_int_other(self, current, previous):
        if current.value > previous.value:
            return 1
        elif current.value < previous.value:
            return -1
        return 0

    def _cmp_float_other(self, current, previous):
        if round(current.value, 3) > round(previous.value,3):
            return 1
        if round(current.value, 3) < round(previous.value, 3):
            return -1
        return 0







