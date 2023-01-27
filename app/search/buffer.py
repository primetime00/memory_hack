import ctypes
from typing import Union

from app.helpers.exceptions import BufferException
from app.search.converters import FloatConvert
from app.search.operations import ValueOperation, MemoryOperation, EqualFloat
from app.search.value import Value, FloatValue, IntValue, AOB

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class SearchBuffer:
    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable=None, store_size:int=1, _results: list=None, result_write_threshold:int =10000):
        self.buffer = buffer
        self.store_size = store_size
        self.start_offset = start_offset
        self.result_callback = _result_callback
        self.result_threshold = result_write_threshold
        self.ptr = ctypes.cast(self.buffer, ctypes.POINTER(ctypes.c_ubyte))

        self.results = [] if _results is None else _results


    def __len__(self):
        return len(self.buffer)

    def find_value(self, value: Value):
        pass

    def find_by_operation(self, operation: ValueOperation, args=None):
        pass

    def fb_cb(self, results, i, read):
        results.append((self.start_offset + (i * self.store_size), self._value_to_bytes(read)))
        if self.result_callback and len(results) >= self.result_threshold:
            self.result_callback(results)
            results.clear()

    def compare_by_operation(self, compare_buffer: "SearchBuffer", operation: MemoryOperation):
        if type(self) != type(compare_buffer):
            raise BufferException("Cannot compare buffers of type {} and {}".format(str(type(self)), str(type(compare_buffer))))
        if not isinstance(operation, MemoryOperation):
            raise BufferException('Comparing buffers require a memory operation.')
        length = min(len(self), len(compare_buffer))
        ptr1 = self.ptr
        ptr2 = compare_buffer.ptr
        operation.run(ptr1, ptr2, length, self.fb_cb, self.results)
        return length*self.store_size

    def read(self, index):
        if index < 0 or index >= len(self.buffer) - (self.store_size-1):
            raise IndexError()
        return self._read(index)

    def _read(self, index):
        return ctypes.c_byte.from_buffer(self.buffer, index)

    def _index_to_address(self, index):
        return index*self.store_size

    def _value_to_bytes(self, value):
        return bytes(ctypes.c_byte(value))

    def get_store_size(self):
        return self.store_size

    def get_start_offset(self):
        return self.start_offset


    @staticmethod
    def create(buffer, start_offset, search_value: Value, result_callback: callable=None, _results: list=None, result_write_threshold:int =10000):
        if type(search_value) == IntValue:
            return IntSearchBuffer(buffer, start_offset, result_callback, search_value.store_size, _results, result_write_threshold)
        elif type(search_value) == FloatValue:
            return FloatSearchBuffer(buffer, start_offset, result_callback, _results, result_write_threshold)
        elif type(search_value) == AOB:
            return AOBSearchBuffer(buffer, start_offset, result_callback, search_value.get_store_size(), _results, result_write_threshold)
        raise BufferException('could not create buffer of type ' + str(search_value))


class IntSearchBuffer(SearchBuffer):
    report_increment = 4000000

    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable=None, store_size=1, _results: list=None, result_write_threshold:int =10000):
        super().__init__(buffer, start_offset, _result_callback, store_size, _results, result_write_threshold)
        self.store_size = store_size
        self.read_map = {1: self._read1,
                         2: self._read2,
                         4: self._read4,
                         8: self._read8}
        self.type_map = {
                            1: ctypes.c_uint8,
                            2: ctypes.c_uint16,
                            4: ctypes.c_uint32,
                            8: ctypes.c_uint64
                        }
        if store_size not in list(self.read_map.keys()):
            raise BufferException("invalid store size of {}".format(store_size))
        self.ptr = ctypes.cast(self.buffer, ctypes.POINTER(self.type_map[store_size]))

    def __len__(self):
        return int(super().__len__() / self.store_size)

    def find_value(self, value: IntValue):
        return self._haystack_search(value)

    def _read1(self, index):
        return self.ptr[index]

    def _read2(self, index):
        return self.ptr[index]

    def _read4(self, index):
        return self.ptr[index]

    def _read8(self, index):
        return self.ptr[index]

    def _read(self, index):
        return self.ptr[index]

    def _value_to_bytes(self, value):
        return bytes(self.type_map[self.store_size](value))

    def _haystack_search(self, value: IntValue):
        haystack = bytes(self.buffer)
        needle = value.bytes
        start = 0
        result = haystack.find(needle, start)
        while start < len(haystack) and result != -1:
            if (result+self.start_offset) % self.store_size == 0:
                self.results.append((result+self.start_offset, needle))
                if self.result_callback and len(self.results) >= self.result_threshold:
                    self.result_callback(self.results)
                    self.results.clear()
            start = result + 1
            result = haystack.find(needle, start)
        if self.result_callback and len(self.results) >= self.result_threshold:
            self.result_callback(self.results)
            self.results.clear()
        return len(haystack)

    def find_by_operation(self, operation:ValueOperation, args=None):
        length = int(len(self.buffer) / self.store_size)
        operation.run(self.ptr, length, self.fb_cb, self.results)
        return len(self.buffer)


class FloatSearchBuffer(SearchBuffer):
    report_increment = 4000000

    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable=None, _results: list=None, result_write_threshold:int =10000):
        super().__init__(buffer, start_offset, _result_callback, 4, _results, result_write_threshold)
        self.ptr = ctypes.cast(self.buffer, ctypes.POINTER(ctypes.c_float))

    def __len__(self):
        return int(super().__len__()/4)

    def find_value(self, value: FloatValue):
        search_value = value.get_comparable_value()
        length = self.__len__()
        op = EqualFloat(search_value)
        op.run(self.ptr, length, self.fb_cb, self.results)
        return length*self.store_size

    def find_by_operation(self, operation: ValueOperation, args=None):
        length = self.__len__()
        operation.run(self.ptr, length, self.fb_cb, self.results)
        return length * self.store_size

    def _read(self, index):
        return self.ptr[index]

    def _value_to_bytes(self, value):
        return FloatConvert().to_bytes(value)

class AOBSearchBuffer(SearchBuffer):
    report_increment = 4000000

    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable=None, store_size=4, _results: list=None, result_write_threshold:int =10000):
        super().__init__(buffer, start_offset, _result_callback, store_size, _results, result_write_threshold)

    def find_value(self, value: AOB):
        return self._haystack_search(value)

    def aob_match(self, haystack, aob_bytes, start: int):
        aob_index = -1
        for i in range(start, start + len(aob_bytes)):
            aob_index += 1
            if aob_bytes[aob_index] >= 256:
                continue
            if int(haystack[i]) != aob_bytes[aob_index]:
                return False
        return True

    def _haystack_find(self, haystack: bytes, needle: bytes, start: int, aob_bytes, search_offset: int):
        while True:
            result = haystack.find(needle, start)
            if result == -1:
                return -1
            start = result-search_offset
            if start < 0:
                return -1
            if start+len(aob_bytes) >= len(haystack):
                return -1
            if not self.aob_match(haystack, aob_bytes, start):
                start += len(aob_bytes)
                if start >= len(haystack):
                    return -1
                continue
            break
        return start

    def _haystack_search(self, value: AOB):
        haystack = bytes(self.buffer)
        needle = bytes(value.value.get_search_value())
        start = 0
        result = self._haystack_find(haystack, needle, start, value.value.aob_item['aob_bytes'], value.value.get_offset())
        value_length = len(value.value.get_array())
        while start < len(haystack) and result != -1:
            self.results.append( (result+self.start_offset, bytes(self.buffer[result:result+value_length])) )
            if self.result_callback and len(self.results) >= self.result_threshold:
                self.result_callback(self.results)
                self.results.clear()
            start = result + 1 + value.value.get_offset()
            result = self._haystack_find(haystack, needle, start, value.value.aob_item['aob_bytes'], value.value.get_offset())
        if self.result_callback and len(self.results) > 0:
            self.result_callback(self.results)
            self.results.clear()
        return len(haystack)

    def find_by_operation(self, operation:ValueOperation, args=None):
        _type = ctypes.c_byte
        results = []
        length = len(self.buffer) - self.store_size
        operation.run(self.ptr, length, self.fb_cb, results)
        if self.result_callback and len(results) > 0:
            self.result_callback(results)
            results.clear()
        return length

    def _read(self, index):
        return bytes((ctypes.c_byte*self.store_size).from_buffer(self.buffer, index))

    def _index_to_address(self, index):
        return index


