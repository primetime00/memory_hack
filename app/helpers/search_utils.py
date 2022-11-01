import copy
import ctypes
import os
import shutil
from typing import List, Union

import multiprocess
from mem_edit import Process

from app.helpers.aob_value import AOBValue
from app.helpers.directory_utils import memory_directory
from app.helpers.exceptions import SearchException, BreakException
from app.helpers.operation_control import OperationControl
from app.helpers.progress import Progress
from app.helpers.search_results import SearchResults
from app.helpers.search_value import SearchValue

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]



class SearchUtilities:
    mem_path = memory_directory
    max_capture_size = int((25600000/4) * (4/multiprocess.cpu_count()))
    def __init__(self, mem: Process, value: SearchValue, results: SearchResults, op_control: OperationControl = None, progress:Progress = None):
        self.mem = mem
        self.value = value
        self.results = results
        if op_control:
            self.op_control = op_control
        else:
            self.op_control = OperationControl()
        if progress:
            self.progress = progress
        else:
            self.progress = Progress()
        self.total_size, self.mem_start, self.mem_end = self.get_total_memory_size()
        self.dump_index = 0

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
            total += (stop-start)
        return total, _start, _end

    def search_all_memory(self, filter_func = None):
        self.progress.add_constraint(0, self.total_size, 1.0)
        for start, stop in self.mem.list_mapped_regions(True):
            try:
                self.op_control.test()
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                self._haystack_search(self.value.get_search_value(), region_buffer, filter_func=filter_func, offset=start)
            except OSError:
                pass
        self.progress.mark()
        return self.results

    def walk_all_memory(self, cmp):
        self.progress.add_constraint(0, self.total_size, 1.0)
        mem_walker = SearchUtilities.memory_walker(self.mem, copy.copy(self.value.get_type()(0)))
        for read, addr, count in mem_walker:
            self.op_control.test()
            if cmp(read):
                self.results.add(addr, read)
            self.progress.increment(1)
        self.progress.mark()
        return self.results

    def search_addresses(self, results: SearchResults, cmp_func = None) -> SearchResults:
        self.progress.add_constraint(0, len(results), 1.0)
        current_read = copy.copy(self.value.get_type()(0))
        if not cmp_func:
            def cmp_func(buffer: ctypes_buffer_t):
                return self.value.equals(buffer)

        for result in results:
            address = result['address']
            self.op_control.test()
            try:
                self.mem.read_memory(address, current_read)
                if cmp_func(current_read):
                    self.results.add(address, type(current_read).from_buffer_copy(current_read))
            except OSError:
                pass
            self.progress.increment(1)
        results.clear()
        self.progress.mark()
        return self.results

    def _haystack_search(self, needle_buffer: ctypes_buffer_t, haystack_buffer: ctypes_buffer_t, filter_func = None, offset=0):
        haystack = bytes(haystack_buffer)
        needle = bytes(needle_buffer)

        start = 0
        last_result = 0
        result = haystack.find(needle, start)
        while start < len(haystack) and result != -1:
            self.op_control.test()
            if filter_func:
                filter_func(haystack_buffer, result, offset)
            else:
                self.results.add(result+offset, needle_buffer)
            self.progress.increment(result-last_result)
            start = result + 1
            last_result = result
            result = haystack.find(needle, start)
        self.progress.increment(len(haystack) - last_result)

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

    def capture_memory_range(self, _position, _range):
        if self.mem_path.absolute().exists():
            shutil.rmtree(self.mem_path.absolute())
        mem_list = list(self.mem.list_mapped_regions())
        self.progress.add_constraint(0, mem_list[-1][1], 1.0)
        self.mem_path.mkdir(exist_ok=True)
        abs_start = mem_list[0][0]
        if _position < abs_start:
            raise SearchException("Could not search around this position")

        for start, stop in self.mem.list_mapped_regions():
            self.op_control.test()
            if _position < start or _position >= stop:
                continue
            _start = int(max((_position - _range/2), start))
            _end = int(min((_position + _range/2), stop))
            cap_file = self.mem_path.joinpath('capture_{}_{}'.format(_start-abs_start, (_end-_start)))
            try:
                region_buffer = (ctypes.c_byte * (_end - _start))()
                self.mem.read_memory(_start, region_buffer)
                cap_file.write_bytes(bytes(region_buffer))
                break
            except OSError:
                continue
        self.progress.mark()


    def capture_memory(self):
        if self.mem_path.absolute().exists():
            shutil.rmtree(self.mem_path.absolute())
        mem_list = list(self.mem.list_mapped_regions())
        self.progress.add_constraint(0, mem_list[-1][1], 1.0)
        self.mem_path.mkdir(exist_ok=True)
        abs_start = mem_list[0][0]
        for start, stop in self.mem.list_mapped_regions():
            self.op_control.test()
            size = stop-start
            pos = start
            iterations = [size]
            if size > self.max_capture_size:
                iterations = [self.max_capture_size] * int(size/self.max_capture_size)
                iterations.append(size - int(size/self.max_capture_size) * self.max_capture_size)
            try:
                for it in iterations:
                    cap_file = self.mem_path.joinpath('capture_{}_{}'.format(pos - abs_start, (it)))
                    with open(cap_file, 'wb') as f:
                        region_buffer = (ctypes.c_byte * it)()
                        self.mem.read_memory(pos, region_buffer)
                        f.write(bytes(region_buffer))
                        pos += it
                self.progress.set(stop)
            except OSError:
                continue
        self.progress.mark()

    def search_cmp_capture(self, cmp_func) -> SearchResults:
        if not self.mem_path.absolute().exists():
            raise SearchException('cannot find capture')
        total_size = 0
        total_count = 0
        for f in self.mem_path.glob('*'):
            total_size += os.path.getsize(f)
            total_count += 1
        if total_size > 6000000 and total_count > 4:
            return self._search_cmp_capture_multi(cmp_func)
        return self._search_cmp_capture_single(cmp_func)

    def _pool_process(self, data):
        #mm_interval.append((file, start, size, abs_start, queue, cmp_func, self.value))
        f_name = data[0]
        start = data[1]
        size = data[2]
        abs_start = data[3]
        queue: multiprocess.Queue = data[4]
        cmp_func = data[5]
        value: SearchValue = data[6]
        res_list = []
        last = 0
        tp = value.get_type()
        try:
            cap_file = self.mem_path.joinpath(f_name)
            read_bytes = cap_file.read_bytes()
            capture_buffer = (ctypes.c_byte * len(read_bytes))(*read_bytes)
            region_buffer = (ctypes.c_byte * size)()
            self.mem.read_memory(abs_start+start, region_buffer)
            cmp_size = size - (value.get_size() - 1)
            for i in range(0, cmp_size, value.get_size()):
                mem_value = tp.from_buffer(region_buffer, i)
                cap_value = tp.from_buffer(capture_buffer, i)
                if cmp_func(mem_value, cap_value, value):
                    res_list.append( (abs_start+start+i, bytearray(mem_value)) )
                if i % 18000 == 0 or i == size-1:
                    queue.put([0, os.getpid(), i-last])
                    last = i
                if len(res_list) >= 100000 or (i == size-1 and len(res_list) > 0):
                    queue.put([1, os.getpid(), res_list])
                    res_list.clear()
            return os.getpid()
        except OSError:
            queue.put([0, os.getpid(), size])
            if len(res_list) > 0:
                queue.put([1, os.getpid(), res_list])
            res_list.clear()
            return os.getpid()

    def _search_cmp_capture_multi(self, cmp_func) -> SearchResults:
        manager = multiprocess.Manager()
        queue: multiprocess.context.BaseContext.Queue = manager.Queue(maxsize=10000)
        mem_list = list(self.mem.list_mapped_regions())
        abs_start = mem_list[0][0]
        self.progress.add_constraint(0, self.total_size, 1.0)
        mm_interval = []
        sr_map = {}
        index=1
        recv_bytes = 0

        import time
        start_time = time.time()
        samples = 0

        s_list = [(x.stem, int(x.stem.split('_')[1]), int(x.stem.split('_')[2])) for x in sorted(list(self.mem_path.glob('capture*')))]
        for s in s_list:
            mm_interval.append((s[0], s[1], s[2], abs_start, queue, cmp_func, self.value))
            index += 1
        with multiprocess.get_context("spawn").Pool(processes=max(1, multiprocess.cpu_count()-1)) as pool:
            try:
                res = pool.map_async(self._pool_process, mm_interval)
                while not res.ready():
                    now = time.time()
                    if (now - start_time) >= 5:
                        samples += 1
                        print("MBps = {}".format(recv_bytes / 1000000 / samples))
                        start_time = now

                    if not queue.empty():
                        self.op_control.test()
                        st, pid, dt = queue.get()
                        if st == 0:
                            recv_bytes += dt
                            self.progress.set(recv_bytes)
                        else:
                            for d in dt:
                                self.results.add(d[0], self.value.get_type().from_buffer(d[1]))
                        continue
                    res.wait(1.0)
                    self.op_control.test()
                    self.progress.set(recv_bytes)
                res.get()
            except BreakException as e:
                pool.terminate()
                pool.join()
                raise e
        for k, v in sr_map.items():
            self.results.extend(v)
        self.progress.mark()
        return self.results

    def _search_cmp_capture_single(self, cmp_func) -> SearchResults:
        mem_list = list(self.mem.list_mapped_regions())
        abs_start = mem_list[0][0]
        count = 0
        last = 0
        self.progress.add_constraint(0, self.total_size, 1.0)
        for f in self.mem_path.glob('*'):
            try:
                start = abs_start+int(f.parts[-1].split('_')[1])
                stop = start+int(f.parts[-1].split('_')[2])
                cap_file = f
                read_bytes = cap_file.read_bytes()
                capture_buffer = (ctypes.c_byte * len(read_bytes))(*read_bytes)
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                size = (stop - start) - (self.value.get_size() - 1)
                cmp_size = size - (self.value.get_size() - 1)
                for i in range(0, cmp_size, self.value.get_size()):
                    mem_value = self.value.get_type().from_buffer(region_buffer, i)
                    cap_value = self.value.get_type().from_buffer(capture_buffer, i)
                    count += 1
                    if count % 4096 == 0:
                        self.progress.increment(count - last)
                        last = count
                    if cmp_func(mem_value, cap_value, self.value):
                        self.results.add(start+i, self.value.get_type().from_buffer_copy(region_buffer, i))
            except OSError:
                continue
        self.progress.mark()
        return self.results

    def search_cmp_addresses(self, results: SearchResults, cmp_func = None) -> SearchResults:
        self.progress.add_constraint(0, len(results), 1.0)
        for result in results:
            address = result['address']
            read = result['value']
            self.op_control.test()
            read_buffer = copy.copy(self.value.get_type()(0))
            try:
                self.mem.read_memory(address, read_buffer)
                if cmp_func(read_buffer, read, self.value):
                    self.results.add(address, read_buffer)
            except OSError:
                pass
            self.progress.increment(1)
        self.progress.mark()
        results.clear()
        return self.results

    def search_aob_all_memory(self) -> SearchResults:
        def filter(haystack, offset, start_offset: int):
            j = 0
            buf = ctypes.cast(haystack, ctypes.POINTER(ctypes.c_ubyte))
            size = self.value.get_size()
            start = offset-self.value.get_offset()
            end = start + size
            if start < 0:
                return
            if end >= len(haystack):
                return
            for i in range(start, end):
                bt = self.value.get_byte(j)
                j += 1
                if bt >= 256:
                    continue
                if bt != buf[i]:
                    return
            self.results.add(start_offset+start, self.value.get_type()(*buf[start:end]))
        addrs = self.search_all_memory(filter_func=filter)
        return addrs

    def search_aob_addresses(self, value: str, search_results: List, cmp_func):
        val = AOBValue(value)
        found = []
        for i in range(len(search_results)-1, -1, -1):
            item = search_results[i]
            addr = item['address']
            size = val.aob_item['size']
            try:
                read = self.mem.read_memory(addr, (ctypes.c_ubyte*size)())
                if cmp_func(read, item['value'], val.aob_item['aob_bytes']):
                    found.append((item['address'], read))
            except OSError:
                pass
        return found

    def search_aob_cmp(self, search_results: List, cmp_func):
        found = []
        for i in range(len(search_results)-1, -1, -1):
            item = search_results[i]
            addr = item['address']
            size = ctypes.sizeof(search_results[0]['value'])
            try:
                read = self.mem.read_memory(addr, (ctypes.c_ubyte*size)())
                if cmp_func(read, item['value']):
                    found.append((item['address'], read))
            except OSError:
                pass
        return found

    def compare_aob(self, addr:int, aob:str):
        res = True
        values = aob.upper().split()
        new_values = []
        try:
            mem = self.mem.read_memory(addr, (ctypes.c_byte * len(values))())
            for i in range(0, len(mem)):
                new_values.append('{0:0{1}X}'.format((mem[i] + (1 << 8)) % (1 << 8), 2))
                if values[i] == '??':
                    continue
                orig = bytes.fromhex(values[i])
                if res and orig[0] != ((mem[i] + (1 << 8)) % (1 << 8)):
                    res = False
        except OSError:
            res = False
            new_values = ['invalid']
        return res, new_values, values

    def get_process_memory(self):
        return self.mem

    def call_break(self):
        self.op_control.control_break()

    @classmethod
    def delete_memory(cls):
        for x in cls.mem_path.glob('*'):
            os.unlink(x)

    def search_memory(self):
        if self.value.is_aob():
            return self.search_aob_all_memory()
        else:
            return self.search_all_memory()



