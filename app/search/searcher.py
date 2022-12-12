import copy
import ctypes
import shutil
from typing import Union

from mem_edit import Process

from app.helpers.aob_value import AOBValue
from app.helpers.directory_utils import memory_directory
from app.helpers.exceptions import BreakException
from app.helpers.exceptions import SearchException
from app.helpers.progress import Progress
from app.helpers.search_results import SearchResults
from app.helpers.timer import PollTimer
from app.search.buffer import SearchBuffer
from app.search.operations import Operation, MemoryOperation, EqualInt, EqualFloat, EqualArray
from app.search.value import Value, IntValue

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class Searcher:
    def __init__(self, memory: Process, progress: Progress = None, write_only=True, directory=memory_directory):
        self.memory = memory
        self.write_only = write_only
        self.include_paths = []
        self.total_size, self.mem_start, self.mem_end = self.get_total_memory_size()
        self.dump_index = 0
        self.progress = progress
        self.search_size = None
        self.signed = True
        self.results: SearchResults = None
        self.capture_files = []
        self.cancel_search = False
        self.cancel_event = None
        self.max_capture_size = 25600000
        self.mem_path = directory

    def copy(self):
        ret = copy.deepcopy(self)
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*self.results.store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        self.results = SearchResults.from_result(self.results, sv.store_size)
        return ret

    def set_include_paths(self, paths: list):
        self.include_paths = paths
        self.total_size, self.mem_start, self.mem_end = self.get_total_memory_size()

    def get_regions(self):
        return self.memory.list_mapped_regions(writeable_only=self.write_only, include_paths=self.include_paths)

    def setup_by_value(self, sv: Value):
        self.set_search_size(sv.get_store_type())

    def set_search_size(self, search_size: str):
        self.search_size = search_size

    def set_signed(self, _sign):
        self.signed = _sign

    def set_results(self, name="default", value=Value.create("0", "byte_4")):
        self.results = SearchResults(name=name, store_size=value.get_store_size())

    def get_total_memory_size(self):
        total = 0
        ls = list(self.get_regions())
        _start = ls[0][0]
        _end = ls[-1][1]
        for start, stop in self.get_regions():
            total += (stop-start)
        return total, _start, _end

    def prepare_memory_search(self):
        self.total_size, self.mem_start, self.mem_end = self.get_total_memory_size()

    def clear_files(self):
        if self.mem_path.absolute().exists():
            shutil.rmtree(self.mem_path.absolute())
        if self.capture_files:
            self.capture_files.clear()
        self.mem_path.mkdir(exist_ok=True)

    def has_results(self):
        return self.results is not None

    def has_captures(self):
        return len(self.capture_files) > 0

    def capture_memory(self):
        self.clear_files()
        self.prepare_memory_search()
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)
        for start, stop in self.get_regions():
            size = stop-start
            pos = start
            iterations = [size]
            if size > self.max_capture_size:
                iterations = [self.max_capture_size] * int(size/self.max_capture_size)
                iterations.append(size - int(size/self.max_capture_size) * self.max_capture_size)

            for it in iterations:
                cap_file = self.mem_path.joinpath('capture_{}_{}'.format(pos - self.mem_start, it))
                try:
                    self.check_cancel()
                    region_buffer = (ctypes.c_byte * it)()
                    self.memory.read_memory(pos, region_buffer)
                except OSError:
                    if self.progress:
                        self.progress.increment(it)
                    continue
                with open(cap_file, 'wb') as f:
                    f.write(bytes(region_buffer))
                    self.capture_files.append(cap_file)
                    if self.progress:
                        self.progress.increment(it)
                    pos += it
        if self.progress:
            self.progress.mark()

    def capture_memory_range(self, _position, _range):
        self.prepare_memory_search()
        if self.mem_path.absolute().exists():
            shutil.rmtree(self.mem_path.absolute())
        if self.capture_files:
            self.capture_files.clear()
        self.mem_path.mkdir(exist_ok=True)
        if _position < self.mem_start:
            raise SearchException("Could not search around this position")
        #find out location
        loc_start = -1
        loc_stop = -1
        for start, stop in self.get_regions():
            if _position < start or _position >= stop:
                continue
            loc_start = start
            loc_stop = stop
        if loc_start < 0:
            raise SearchException("Could find memory location to capture")

        _start = int(max((_position - _range/2), loc_start))
        _end = int(min((_position + _range/2), loc_stop))
        if self.progress:
            self.progress.add_constraint(0, _end-_start, 1.0)
        cap_file = self.mem_path.joinpath('capture_{}_{}'.format(_start-self.mem_start, (_end-_start)))
        try:
            region_buffer = (ctypes.c_byte * (_end - _start))()
            self.memory.read_memory(_start, region_buffer)
            cap_file.write_bytes(bytes(region_buffer))
            self.capture_files.append(cap_file)
        except OSError:
            raise SearchException("Could read memory location to capture")
        if self.progress:
            self.progress.mark()

    def _result_callback(self, _results):
        [self.results.add(res['address'], res['value']) for res in _results]
        _results.clear()

    def search_memory_value(self, value: str):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        self.prepare_memory_search()
        self.delete_previous_results_and_captures()
        sv = Value.create(value, self.search_size)
        self.results.store_size = sv.store_size
        self.signed = sv.is_signed() if isinstance(sv, IntValue) else False
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)
        for start, stop in self.get_regions():
            try:
                self.check_cancel()
                i_start = start
                while True:
                    size = min(stop - i_start, self.max_capture_size)
                    if size <= 0:
                        break
                    region_buffer = (sv.get_ctype() * size)()
                    self.memory.read_memory(i_start, region_buffer)
                    search_buffer = SearchBuffer.create(region_buffer, i_start, sv, self._result_callback, progress_callback=self.progress.increment if self.progress else None, cancel_callback=self.check_cancel)
                    search_buffer.find_value(sv)
                    i_start += size
            except OSError:
                pass
        if self.progress:
            self.progress.mark()

    def search_memory_operation(self, operation, args=None):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        self.prepare_memory_search()
        self.delete_previous_results_and_captures()
        sv = Value.create("0", self.search_size)
        self.results.store_size = sv.store_size
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)
        for start, stop in self.get_regions():
            try:
                self.check_cancel()
                i_start = start
                while True:
                    size = min(stop - i_start, self.max_capture_size)
                    if size <= 0:
                        break
                    region_buffer = (sv.get_ctype() * size)()
                    self.memory.read_memory(i_start, region_buffer)
                    search_buffer = SearchBuffer.create(region_buffer, i_start, sv, self._result_callback, progress_callback=self.progress.increment if self.progress else None, cancel_callback=self.check_cancel)
                    search_buffer.find_by_operation(operation, args)
                    i_start += size
            except OSError:
                pass
        if self.progress:
            self.progress.mark()

    def _search_continue_value_results(self, sv: Value):
        if self.progress:
            self.progress.add_constraint(0, len(self.results), 1.0)
        last = 0
        if sv.get_store_type() == 'array':
            op = EqualArray(AOBValue(sv.get_printable()).aob_item['aob_bytes'])
        elif sv.get_store_type() == 'float':
            op = EqualFloat(sv.get())
        else:
            op = EqualInt(sv.get())
        new_results = SearchResults.from_result(self.results, sv.store_size)
        for i in range(0, len(self.results)):
            res = self.results[i]
            addr = res['address']
            try:
                read = sv.read_bytes_from_memory(self.memory, addr)
                if op.operation(sv.from_bytes(read)):
                    res['value'] = read
                    new_results.add_r(res)
            except OSError:
                pass
            if self.progress and i % 20 == 0 and i > 0:
                self.progress.increment(i - last)
                last = i
        self.results = new_results
        if self.progress:
            self.progress.increment(len(self.results) - last - 1)

    def search_continue_value(self, value: str):
        if self.results is None or len(self.results) == 0:
            self.search_memory_value(value)
            return
        sv = Value.create(value, self.search_size)
        self.signed = sv.is_signed() if isinstance(sv, IntValue) else False
        self._search_continue_value_results(sv)


    def _search_continue_operation_result(self, operation: Operation):
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*self.results.store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        new_results = SearchResults.from_result(self.results, sv.store_size)
        if isinstance(operation, MemoryOperation):
            def run_op(res):
                addr = res['address']
                read = sv.read_bytes_from_memory(self.memory, addr)
                prev_value = sv.from_bytes(res['value'])
                op_test = operation.run(sv.from_bytes(read), prev_value)
                if op_test:
                    res['value'] = read
                return op_test
        else:
            def run_op(res):
                addr = res['address']
                read = sv.read_bytes_from_memory(self.memory, addr)
                op_test = operation.run(sv.from_bytes(read))
                if op_test:
                    res['value'] = read
                return op_test
        if self.progress:
            self.progress.add_constraint(0, len(self.results), 1.0)
        ct = PollTimer(0.5)
        pt = PollTimer(0.5)
        count = 1
        last = 0
        for res in self.results:
            if run_op(res):
                new_results.add_r(res)
            if ct.has_elapsed():
                self.check_cancel()
            if pt.has_elapsed():
                self.progress.increment(count - last)
                last = count
            count += 1
        self.results = new_results

    def _search_continue_capture_operation(self, operation: MemoryOperation):
        self.prepare_memory_search()
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*self.results.store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)
        for f in self.capture_files:
            start = self.mem_start + int(f.parts[-1].split('_')[1])
            stop = start + int(f.parts[-1].split('_')[2])
            cap_file = f
            try:
                read_bytes = cap_file.read_bytes()
                capture_buffer = (sv.get_ctype() * len(read_bytes))(*read_bytes)
                region_buffer = (sv.get_ctype() * (stop - start))()
                self.memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, self._result_callback, progress_callback=self.progress.increment if self.progress else None, cancel_callback=self.check_cancel)
                compare_buffer = SearchBuffer.create(capture_buffer, start, sv, self._result_callback)
                search_buffer.compare_by_operation(compare_buffer, operation)
            except OSError:
                if self.progress:
                    self.progress.increment(stop-start)
                continue
        self.progress.mark()


    def search_continue_operation(self, operation: Operation):
        if self.results and len(self.results) > 0: #we will do a continuation of a result search
            if self.progress:
                self.progress.reset()
            self._search_continue_operation_result(operation)
        elif len(self.capture_files) > 0: #we will do a capture comparison
            if not isinstance(operation, MemoryOperation):
                raise SearchException('Cannot continue search with this type of operation.')
            if self.progress:
                self.progress.reset()
            self.results = SearchResults(name=type(operation).__name__, store_size=self.search_size_to_count(self.search_size))
            self._search_continue_capture_operation(operation)
        else:
            raise SearchException('Cannot continue search with no results or capture files')


    def cancel(self):
        self.cancel_search = True

    def check_cancel(self):
        if self.cancel_search:
            if self.cancel_event:
                self.cancel_event.set()
            raise BreakException()

    def delete_previous_results_and_captures(self):
        for res in self.capture_files:
            res.unlink(missing_ok=True)
        if self.results:
            self.results.clear()

    @staticmethod
    def clear_captures_and_results():
        for res in SearchResults.directory.glob("*.res"):
            res.unlink(missing_ok=True)
        for res in SearchResults.directory.glob("capture*"):
            res.unlink(missing_ok=True)

    @staticmethod
    def search_size_to_count(search_size):
        if search_size == 'byte_2':
            return 2
        elif search_size == 'byte_1':
            return 1
        else:
            return 4



