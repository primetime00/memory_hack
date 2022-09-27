from mem_edit import Process
from app.helpers.operation_control import OperationControl
from app.helpers.progress import Progress
from app.helpers.aob_value import AOBValue
import ctypes, time, copy
from typing import List, Union
from app.helpers.exceptions import SearchException
from pathlib import Path
import shutil, os

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]
class SearchUtilities:
    def __init__(self, mem: Process, op_control: OperationControl = None, progress:Progress = None):
        self.mem = mem
        if op_control:
            self.op_control = op_control
        else:
            self.op_control = OperationControl()
        if progress:
            self.progress = progress
        else:
            self.progress = Progress()
        self.total_size, self.mem_start, self.mem_end = self.get_total_memory_size()

    class memory_walker():
        def __init__(self, memory, value_type):
            self.memory = memory
            self.value_type = value_type
            self.num = 0
            self.regions = list(memory.list_mapped_regions(True))
            self.regionIndex = 0
            self.byteIndex = 0
            self.size = 0
            self.count = 0
            self.current_region = self.read_region()

        def __iter__(self):
            return self

        def __next__(self):
            return self.next()

        def read_region(self):
            while True:
                start = self.regions[self.regionIndex][0]
                end = self.regions[self.regionIndex][1]
                self.size = end-start
                region_buffer = (ctypes.c_byte * self.size)()
                try:
                    self.memory.read_memory(start, region_buffer)
                except OSError:
                    self.regionIndex += 1
                    self.count += self.size
                    continue
                break
            return region_buffer

        def _get_count(self):
            r = self.count
            self.count = 0
            return r

        def eof(self):
            return self.regionIndex >= len(self.regions)
        def increment(self):
            self.byteIndex += 1
            self.count += 1
            if self.byteIndex >= self.size-(ctypes.sizeof(self.value_type)-1):
                self.regionIndex += 1
                self.byteIndex = 0
                self.count = 0
                if self.regionIndex < len(self.regions):
                    self.current_region = self.read_region()
        def next(self):
            if self.eof():
                raise StopIteration()
            while True:
                region = self.regions[self.regionIndex]
                read = self.value_type.__class__.from_buffer(self.current_region, self.byteIndex)
                result = read, region[0] + self.byteIndex, self._get_count()+1
                self.increment()
                break
            return result

    def get_total_memory_size(self):
        total = 0
        ls = list(self.mem.list_mapped_regions())
        _start = ls[0][0]
        _end = ls[-1][1]
        for start, stop in self.mem.list_mapped_regions():
            try:
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                total += (stop-start)
            except OSError:
                continue
        return total, _start, _end

    def search_all_memory(self, needle_buffer: ctypes_buffer_t, filter_func = None):
        found = []
        self.progress.add_constraint(0, self.total_size, 1.0)
        for start, stop in self.mem.list_mapped_regions(True):
            try:
                self.op_control.test()
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                found += [(offset + start, read) for offset, read in self._haystack_search(needle_buffer, region_buffer, filter_func=filter_func)]
            except OSError:
                pass
        self.progress.mark()
        return found

    def search_addresses(self, user_input: ctypes_buffer_t, results: List, cmp_func, *extra) -> List:
        found = []
        self.progress.add_constraint(0, len(results), 1.0)
        current_read = copy.copy(user_input)
        for result in results:
            address = result['address']
            last_read = result['value']
            self.op_control.test()
            self.mem.read_memory(address, current_read)
            if cmp_func(current_read, last_read, user_input, *extra):
                found.append((address, type(current_read).from_buffer_copy(current_read)))
            self.progress.increment(1)
        self.progress.mark()
        return found

    def search_cmp_memory(self, user_input: ctypes_buffer_t, cmp_func):
        found = []
        self.progress.add_constraint(0, self.total_size, 1.0)
        mem_walker = SearchUtilities.memory_walker(self.mem, copy.copy(user_input))
        for read, addr, count in mem_walker:
            self.op_control.test()
            if cmp_func(read, 0, user_input):
                found.append((addr, type(read).from_buffer_copy(read)))
            self.progress.increment(1)
        self.progress.mark()
        return found

    def _haystack_search(self, needle_buffer: ctypes_buffer_t, haystack_buffer: ctypes_buffer_t, filter_func = None) -> List:
        found = []

        haystack = bytes(haystack_buffer)
        needle = bytes(needle_buffer)

        start = 0
        last_result = 0
        result = haystack.find(needle, start)
        while start < len(haystack) and result != -1:
            self.op_control.test()
            if filter_func:
                filter_func(needle_buffer, haystack_buffer, result, found)
            else:
                found.append((result, needle_buffer))
            self.progress.increment(result-last_result)
            start = result + 1
            last_result = result
            result = haystack.find(needle, start)
        self.progress.increment(len(haystack) - last_result)
        return found

    def capture_memory(self):
        mem_path = Path('.memory')
        if mem_path.absolute().exists():
            shutil.rmtree(mem_path.absolute())
        mem_list = list(self.mem.list_mapped_regions())
        self.progress.add_constraint(0, mem_list[-1][1], 1.0)
        mem_path.mkdir(exist_ok=True)
        abs_start = mem_list[0][0]

        for start, stop in self.mem.list_mapped_regions():
            self.op_control.test()
            cap_file = mem_path.joinpath('capture_{}_{}'.format(start-abs_start, (stop-start)))
            try:
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                cap_file.write_bytes(bytes(region_buffer))
                self.progress.set(stop)
            except OSError:
                continue
        self.progress.mark()

    def search_cmp_capture(self, cmp_buf: ctypes._SimpleCData, cmp_func, *extra) -> List:
        mem_path = Path('.memory')
        if not mem_path.absolute().exists():
            raise SearchException('cannot find capture')
        found = []
        mem_list = list(self.mem.list_mapped_regions())
        abs_start = mem_list[0][0]
        self.progress.add_constraint(0, self.total_size, 1.0)
        for start, stop in self.mem.list_mapped_regions():
            try:
                cap_file = mem_path.joinpath('capture_{}_{}'.format(start-abs_start, (stop-start)))
                read_bytes = cap_file.read_bytes()
                capture_buffer = (ctypes.c_byte * len(read_bytes))(*read_bytes)
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                for i in range(0, (stop-start) - (ctypes.sizeof(cmp_buf)-1)):
                    self.op_control.test()
                    mem_value = cmp_buf.from_buffer(region_buffer, i)
                    cap_value = cmp_buf.from_buffer(capture_buffer, i)
                    if cmp_func(mem_value, cap_value, *extra):
                        found.append((start+i, cmp_buf.from_buffer_copy(region_buffer, i)))
                    self.progress.increment(1)
            except OSError:
                self.progress.increment(stop-start)
                continue
        self.progress.mark()
        return found

    def search_cmp_addresses(self, cmp_buf: ctypes._SimpleCData, cmp_func, results) -> List:
        found = []
        self.progress.add_constraint(0, len(results), 1.0)
        for result in results:
            address = result['address']
            read = result['value']
            self.op_control.test()
            read_buffer = cmp_buf()
            self.mem.read_memory(address, read_buffer)
            if cmp_func(read_buffer, read):
                found.append((address, read_buffer))
            self.progress.increment(1)
        self.progress.mark()
        return found

    def search_aob_all_memory(self, value: str) -> List:
        val = AOBValue(value)
        def filter(needle, haystack, offset, found_list):
            j = 0
            buf = ctypes.cast(haystack, ctypes.POINTER(ctypes.c_ubyte))
            size = val.aob_item['size']
            start = offset-val.get_offset()
            end = start + size
            if start < 0:
                return
            if end >= len(haystack):
                return
            for i in range(start, end):
                bt = val.aob_item['aob_bytes'][j]
                j += 1
                if bt >= 256:
                    continue
                if bt != buf[i]:
                    return
            found_list.append((offset-val.get_offset(), (ctypes.c_ubyte * size)(*buf[offset-val.get_offset():offset-val.get_offset()+size])))

        addrs = self.search_all_memory(val.get_search_value(), filter_func=filter)
        return addrs

    def search_aob_addresses(self, value: str, search_results: List, cmp_func):
        val = AOBValue(value)
        found = []
        for i in range(len(search_results)-1, -1, -1):
            item = search_results[i]
            addr = item['address']
            size = val.aob_item['size']
            read = self.mem.read_memory(addr, (ctypes.c_ubyte*size)())
            if cmp_func(read, item['value'], val.aob_item['aob_bytes']):
                found.append((item['address'], read))
        return found

    def search_aob_cmp(self, search_results: List, cmp_func):
        found = []
        for i in range(len(search_results)-1, -1, -1):
            item = search_results[i]
            addr = item['address']
            size = ctypes.sizeof(search_results[0]['value'])
            read = self.mem.read_memory(addr, (ctypes.c_ubyte*size)())
            if cmp_func(read, item['value']):
                found.append((item['address'], read))
        return found

    def compare_aob(self, addr:int, aob:str):
        res = True
        values = aob.upper().split()
        new_values = []
        mem = self.mem.read_memory(addr, (ctypes.c_byte * len(values))())
        for i in range(0, len(mem)):
            new_values.append('{0:0{1}X}'.format((mem[i] + (1 << 8)) % (1 << 8), 2))
            if values[i] == '??':
                continue
            orig = bytes.fromhex(values[i])
            if res and orig[0] != ((mem[i] + (1 << 8)) % (1 << 8)):
                res = False
        return res, new_values, values

    def get_process_memory(self):
        return self.mem

    def call_break(self):
        self.op_control.control_break()

