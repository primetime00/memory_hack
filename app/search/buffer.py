import ctypes
import math
from typing import List, Union

from app.helpers.exceptions import BufferException
from app.helpers.timer import PollTimer
from app.search.converters import FloatConvert
from app.search.operations import ValueOperation, MemoryOperation
from app.search.value import Value, FloatValue, IntValue, AOB

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class SearchBuffer:
    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable, store_size=1, progress_callback: callable = None, cancel_callback: callable = None):
        self.buffer = buffer
        self.cancel_callback = cancel_callback
        self.progress_callback = progress_callback
        self.store_size = store_size
        self.start_offset = start_offset
        self.result_callback = _result_callback
        self.result_threshold = 10000

    def __len__(self):
        return len(self.buffer)

    def find_value(self, value: Value):
        pass

    def find_by_operation(self, operation: ValueOperation, args=None):
        pass

    def compare_by_operation(self, compare_buffer: "SearchBuffer", operation: MemoryOperation):
        rt = PollTimer(0.5)
        cc = PollTimer(1)
        last = 0
        if type(self) != type(compare_buffer):
            raise BufferException("Cannot compare buffers of type {} and {}".format(str(type(self)), str(type(compare_buffer))))
        if not isinstance(operation, MemoryOperation):
            raise BufferException('Comparing buffers require a memory operation.')
        length = min(len(self), len(compare_buffer))
        results = []
        for i in range(0, length):
            read1 = self.read(i)
            read2 = compare_buffer.read(i)
            if operation.run(read1, read2):
                results.append({'address': self.start_offset + (i * self.store_size), 'value': self._value_to_bytes(read1)})
                if len(results) >= self.result_threshold:
                    self.result_callback(results)
            if self.progress_callback and rt.has_elapsed():
                bts = self._index_to_address(i)
                self.progress_callback(bts - last)
                last = bts
            if self.cancel_callback and cc.has_elapsed():
                self.cancel_callback()
        if len(results) > 0:
            self.result_callback(results)
            results.clear()
        if self.progress_callback:
            self.progress_callback(self._index_to_address(length) - last)

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
    def create(buffer, start_offset, search_value: Value, result_callback: callable, progress_callback: callable = None, cancel_callback: callable = None):
        if type(search_value) == IntValue:
            return IntSearchBuffer(buffer, start_offset, result_callback, search_value.store_size, progress_callback=progress_callback, cancel_callback=cancel_callback)
        elif type(search_value) == FloatValue:
            return FloatSearchBuffer(buffer, start_offset, result_callback, progress_callback=progress_callback, cancel_callback=cancel_callback)
        elif type(search_value) == AOB:
            return AOBSearchBuffer(buffer, start_offset, result_callback, search_value.get_store_size(), progress_callback=progress_callback, cancel_callback=cancel_callback)

        raise BufferException('could not create buffer of type ' + str(search_value))


class IntSearchBuffer(SearchBuffer):
    report_increment = 4000000

    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable, store_size=1, progress_callback: callable = None, cancel_callback: callable = None):
        super().__init__(buffer, start_offset, _result_callback, store_size, progress_callback, cancel_callback)
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
        self.int_ptr = ctypes.cast(self.buffer, ctypes.POINTER(self.type_map[store_size]))

    def __len__(self):
        return int(super().__len__() / self.store_size)

    def find_value(self, value: IntValue):
        self._haystack_search(value)

    def _read1(self, index):
        return self.int_ptr[index]

    def _read2(self, index):
        return self.int_ptr[index]

    def _read4(self, index):
        return self.int_ptr[index]

    def _read8(self, index):
        return self.int_ptr[index]

    def _read(self, index):
        return self.int_ptr[index]

    def _value_to_bytes(self, value):
        return bytes(self.type_map[self.store_size](value))

    def _haystack_search(self, value: IntValue):
        haystack = bytes(self.buffer)
        needle = value.bytes
        results = []
        start = 0
        last_result = 0
        count = 0
        ct = PollTimer(2)
        pt = PollTimer(0.5)
        result = haystack.find(needle, start)
        while start < len(haystack) and result != -1:
            count += 1
            if self.cancel_callback and ct.has_elapsed():
                self.cancel_callback()
            results.append({'address': result+self.start_offset, 'value': needle})
            if self.progress_callback and pt.has_elapsed():
                self.progress_callback(result - last_result)
                last_result = result
            if len(results) >= self.result_threshold:
                self.result_callback(results)
                results.clear()
            start = result + 1
            result = haystack.find(needle, start)
        if len(results) > 0:
            self.result_callback(results)
            results.clear()
        if self.progress_callback:
            self.progress_callback(len(haystack) - last_result)

    def find_by_operation(self, operation:ValueOperation, args=None):
        results = []
        count = 0
        last = 0
        length = int(len(self.buffer) / self.store_size)
        ct = PollTimer(1)
        pt = PollTimer(0.5)
        for i in range(0, length):
            read = self.int_ptr[i]
            if operation.run(read):
                results.append({'address': self.start_offset+(i*self.store_size), 'value': self._value_to_bytes(read)})
                if len(results) >= self.result_threshold:
                    self.result_callback(results)
                    results.clear()
            count += self.store_size
            if self.cancel_callback and ct.has_elapsed():
                self.cancel_callback()
            if self.progress_callback and pt.has_elapsed():
                self.progress_callback(count - last)
                last = count
        if len(results) > 0:
            self.result_callback(results)
            results.clear()
        if self.progress_callback:
            self.progress_callback(count - last)


class FloatSearchBuffer(SearchBuffer):
    report_increment = 4000000

    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable, progress_callback: callable = None, cancel_callback: callable = None):
        super().__init__(buffer, start_offset, _result_callback, 4, progress_callback, cancel_callback)
        self.float_ptr = ctypes.cast(self.buffer, ctypes.POINTER(ctypes.c_float))

    def __len__(self):
        return int(super().__len__()/4)

    def find_value(self, value: FloatValue):
        search_value = value.get_comparable_value()
        results = []
        count = 0
        last = 0
        length = self.__len__()
        ct = PollTimer(1)
        pt = PollTimer(0.5)
        for i in range(0, length):
            read = self.float_ptr[i]
            if math.isclose(read, search_value, abs_tol=0.001):
                results.append({'address': self.start_offset+(i*4), 'value': self._value_to_bytes(read)})
                if len(results) >= self.result_threshold:
                    self.result_callback(results)
                    results.clear()
            count += 4
            if self.cancel_callback and ct.has_elapsed():
                self.cancel_callback()
            if self.progress_callback and pt.has_elapsed():
                self.progress_callback(count-last)
                last = count
        if len(results) > 0:
            self.result_callback(results)
            results.clear()
        if self.progress_callback:
            self.progress_callback(count - last)

    def find_by_operation(self, operation:ValueOperation, args=None):
        _type = ctypes.c_float
        results = []
        count = 0
        last = 0
        length = self.__len__()
        ct = PollTimer(1)
        pt = PollTimer(0.5)
        for i in range(0, length):
            read = self.float_ptr[i]
            if operation.operation(read):
                results.append({'address': self.start_offset+(i*self.store_size), 'value': self._value_to_bytes(read)})
                if len(results) >= self.result_threshold:
                    self.result_callback(results)
                    results.clear()
            count += self.store_size
            if self.cancel_callback and ct.has_elapsed():
                self.cancel_callback()
            if self.progress_callback and pt.has_elapsed():
                self.progress_callback(count-last)
                last = count
        if len(results) > 0:
            self.result_callback(results)
            results.clear()
        if self.progress_callback:
            self.progress_callback(count - last)


    def _read(self, index):
        return self.float_ptr[index]

    def _value_to_bytes(self, value):
        return FloatConvert().to_bytes(value)

class AOBSearchBuffer(SearchBuffer):
    report_increment = 4000000

    def __init__(self, buffer: ctypes_buffer_t, start_offset, _result_callback: callable, store_size, progress_callback: callable = None, cancel_callback: callable = None):
        super().__init__(buffer, start_offset, _result_callback, store_size, progress_callback, cancel_callback)

    def find_value(self, value: AOB):
        self._haystack_search(value)

    def _haystack_find(self, haystack: bytes, needle: bytes, start: int, aob_bytes, search_offset: int):
        result = haystack.find(needle, start)
        if result == -1:
            return -1
        start = result-search_offset
        if start < 0:
            return -1
        if start+len(aob_bytes) >= len(haystack):
            return -1
        aob_index = -1
        for i in range(start, start+len(aob_bytes)):
            aob_index += 1
            if aob_bytes[aob_index] >= 256:
                continue
            if int(haystack[i]) != aob_bytes[aob_index]:
                return -1
        return start

    def _haystack_search(self, value: AOB) -> List:
        haystack = bytes(self.buffer)
        needle = bytes(value.value.get_search_value())
        results = []
        start = 0
        last_result = 0
        ct = PollTimer(2)
        pt = PollTimer(0.5)
        result = self._haystack_find(haystack, needle, start, value.value.aob_item['aob_bytes'], value.value.get_offset())

        while start < len(haystack) and result != -1:
            if self.cancel_callback and ct.has_elapsed():
                self.cancel_callback()
            results.append({'address': result+self.start_offset, 'value': bytes(self.buffer[result:result+len(value.value.get_array())])})
            if len(results) >= self.result_threshold:
                self.result_callback(results)
                results.clear()
            if self.progress_callback and pt.has_elapsed():
                self.progress_callback(result - last_result)
            start = result + 1 + value.value.get_offset()
            last_result = result
            result = self._haystack_find(haystack, needle, start, value.value.aob_item['aob_bytes'], value.value.get_offset())
        if len(results) > 0:
            self.result_callback(results)
            results.clear()
        if self.progress_callback:
            self.progress_callback(len(haystack) - last_result)

    def find_by_operation(self, operation:ValueOperation, args=None):
        _type = ctypes.c_byte
        results = []
        count = 0
        last = 0
        length = len(self.buffer) - self.store_size
        ct = PollTimer(2)
        pt = PollTimer(0.5)
        for i in range(0, length):
            read = self.buffer[i:i+self.store_size]
            if operation.operation(read):
                results.append({'address': self.start_offset+(i*self.store_size), 'value': bytes(read)})
                if len(results) >= self.result_threshold:
                    self.result_callback(results)
                    results.clear()
            count += 1
            if self.cancel_callback and ct.has_elapsed():
                self.cancel_callback()
            if self.progress_callback and pt.has_elapsed():
                self.progress_callback(count-last)
                last = count
        if self.progress_callback:
            self.progress_callback(count - last)
        if len(results) > 0:
            self.result_callback(results)
            results.clear()

    def _read(self, index):
        return bytes((ctypes.c_byte*self.store_size).from_buffer(self.buffer, index))

    def _index_to_address(self, index):
        return index


