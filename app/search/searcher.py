import copy
import ctypes
import os
import time
from typing import Union

from mem_edit import Process

from app.helpers.aob_value import AOBValue
from app.helpers.directory_utils import memory_directory
from app.helpers.exceptions import BreakException
from app.helpers.exceptions import SearchException
from app.helpers.progress import Progress
from app.helpers.search_results import SearchResults
from app.search.buffer import SearchBuffer
from app.search.operations import Operation, MemoryOperation, EqualInt, EqualFloat, EqualArray
from app.search.value import Value, IntValue

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class Searcher:

    SEARCH_RETURN_RESULT = 0
    SEARCH_RETURN_CAPTURE = 1
    SEARCH_RETURN_NONE = 2

    SEARCH_TYPE_CAPTURE = 0
    SEARCH_TYPE_COMPARE_CAPTURE = 1
    SEARCH_TYPE_VALUE = 2
    SEARCH_TYPE_OPERATION = 3
    SEARCH_TYPE_CONTINUE = 4



    def __init__(self, memory: Process, progress: Progress = None, write_only=True, directory=memory_directory, results: SearchResults=None):
        self.memory = memory
        self.write_only = write_only
        self.include_paths = []
        self.total_size, self.mem_start, self.mem_end, self.mem_average = self.get_total_memory_size()
        self.progress:Progress = progress
        self.search_size = None
        self.signed = True
        self.results: SearchResults = None
        self.capture_files = []
        self.cancel_search = False
        self.cancel_event = None
        self.max_capture_size = 25600000
        self.mem_path = directory
        self.last_search_type = Searcher.SEARCH_RETURN_NONE
        self.result_progress_threshold = 1000
        self.result_write_threshold = 10000
        if results is None:
            self.results = SearchResults('results', db_path=directory.joinpath('scripts.db'))
        else:
            self.results = results

    def copy(self):
        ret = copy.deepcopy(self)
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*4), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        self.results = SearchResults(name='tmp_{}'.format(int(time.time() * 1000) % 300000))
        return ret

    def on_search_start(self, search_type: int):
        self.prepare_memory_search()
        if search_type == self.SEARCH_TYPE_CAPTURE:
            self.clear_captures()
            if self.progress:
                self.progress.add_constraint(0, self.total_size, 1.0)
        elif search_type == self.SEARCH_TYPE_COMPARE_CAPTURE:
            if self.progress:
                self.progress.reset()
                self.progress.add_constraint(0, self.total_size, 1.0)
            self.results.delete_database()
            with self.results.db() as conn:
                self.results.create_result_table(conn)
        elif search_type == self.SEARCH_TYPE_VALUE or search_type == self.SEARCH_TYPE_OPERATION:
            self.results.delete_database()
            with self.results.db() as conn:
                self.results.create_result_table(conn)
            if self.progress:
                self.progress.add_constraint(0, self.total_size, 1.0)
        elif search_type == self.SEARCH_TYPE_CONTINUE:
            if self.progress:
                self.progress.reset()
                self.progress.add_constraint(0, len(self.results), 1.0)
            with self.results.db() as conn:
                self.results.increment_result_table(conn)

    def on_search_end(self, search_type: int):
        if search_type == self.SEARCH_TYPE_CAPTURE:
            self.last_search_type = Searcher.SEARCH_RETURN_CAPTURE
        elif search_type == self.SEARCH_TYPE_COMPARE_CAPTURE:
            self.clear_captures()
            self.last_search_type = Searcher.SEARCH_RETURN_RESULT
        elif search_type == self.SEARCH_TYPE_VALUE or search_type == self.SEARCH_TYPE_OPERATION:
            self.last_search_type = Searcher.SEARCH_RETURN_RESULT
        elif search_type == self.SEARCH_TYPE_CONTINUE:
            pass
        if self.progress:
            self.progress.mark()

    def on_search_cancel(self, search_type: int):
        if search_type == self.SEARCH_TYPE_CAPTURE:
            self.clear_captures()
        elif search_type == self.SEARCH_TYPE_COMPARE_CAPTURE:
            pass
        elif search_type == self.SEARCH_TYPE_VALUE:
            pass
        elif search_type == self.SEARCH_TYPE_OPERATION:
            pass
        elif search_type == self.SEARCH_TYPE_CONTINUE:
            with self.results.db() as conn:
                self.results.revert_result_table(conn)
        if self.progress:
            self.progress.mark()



    def set_include_paths(self, paths: list):
        self.include_paths = paths
        self.total_size, self.mem_start, self.mem_end, self.mem_average = self.get_total_memory_size()

    def get_include_paths(self):
        return self.include_paths

    def get_regions(self):
        return self.memory.list_mapped_regions(writeable_only=self.write_only, include_paths=self.include_paths)

    def setup_by_value(self, sv: Value):
        self.set_search_size(sv.get_store_type())

    def set_search_size(self, search_size: str):
        self.search_size = search_size

    def set_signed(self, _sign):
        self.signed = _sign

    def get_total_memory_size(self):
        total = 0
        ls = list(self.get_regions())
        _start = ls[0][0]
        _end = ls[-1][1]
        for start, stop in self.get_regions():
            total += (stop-start)
        average = int(total / len(ls))
        return total, _start, _end, average

    def prepare_memory_search(self):
        self.total_size, self.mem_start, self.mem_end, self.mem_average = self.get_total_memory_size()

    def clear_captures(self):
        if not self.mem_path.absolute().exists():
            self.mem_path.mkdir(exist_ok=True)
        for f in self.mem_path.glob("*.cap"):
            os.unlink(f)

    def has_results(self):
        try:
            return self.results and len(self.results) > 0
        except Exception:
            return False


    def has_captures(self):
        return len(self.capture_files) > 0

    def capture_memory(self):
        self.on_search_start(self.SEARCH_TYPE_CAPTURE)
        for start, stop in self.get_regions():
            size = stop-start
            pos = start
            iterations = [size]
            if size > self.max_capture_size:
                iterations = [self.max_capture_size] * int(size/self.max_capture_size)
                iterations.append(size - int(size/self.max_capture_size) * self.max_capture_size)

            for it in iterations:
                cap_file = self.mem_path.joinpath('capture_{:016X}_{:016X}.cap'.format(pos, pos+it))
                try:
                    self.check_cancel()
                    region_buffer = (ctypes.c_byte * it)()
                    self.memory.read_memory(pos, region_buffer)
                except OSError:
                    if self.progress:
                        self.progress.increment(it)
                    continue
                except BreakException:
                    self.on_search_cancel(self.SEARCH_TYPE_CAPTURE)
                    raise
                with open(cap_file, 'wb') as f:
                    f.write(bytes(region_buffer))
                    self.capture_files.append(cap_file)
                    if self.progress:
                        self.progress.increment(it)
                    pos += it
        self.on_search_end(self.SEARCH_TYPE_CAPTURE)

    def capture_memory_range(self, _position, _range):
        if _position < self.mem_start:
            raise SearchException("Could not search around this position")
        self.on_search_start(self.SEARCH_TYPE_CAPTURE)
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
        cap_file = self.mem_path.joinpath('capture_{:016X}_{:016X}.cap'.format(_start, _start+(_end-_start)))
        try:
            self.check_cancel()
            region_buffer = (ctypes.c_byte * (_end - _start))()
            self.memory.read_memory(_start, region_buffer)
            cap_file.write_bytes(bytes(region_buffer))
            self.capture_files.append(cap_file)
        except OSError:
            raise SearchException("Could read memory location to capture")
        except BreakException:
            self.on_search_cancel(self.SEARCH_TYPE_CAPTURE)
            raise
        self.on_search_end(self.SEARCH_TYPE_CAPTURE)

    def search_memory_value(self, value: str):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        self.on_search_start(self.SEARCH_TYPE_VALUE)
        sv = Value.create(value, self.search_size)
        self.signed = sv.is_signed() if isinstance(sv, IntValue) else False
        _batch_results = []
        with self.results.db() as conn:
            def result_callback(results: list):
                self.results.add_results(conn, results)
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
                        search_buffer = SearchBuffer.create(region_buffer, i_start, sv, result_callback, _batch_results, self.result_write_threshold)
                        count = search_buffer.find_value(sv)
                        if self.progress:
                            self.progress.increment(count)
                        self.check_cancel()
                        i_start += size
                except OSError:
                    continue
                except BreakException:
                    self.on_search_cancel(self.SEARCH_TYPE_VALUE)
                    raise
            if len(_batch_results) > 0:
                result_callback(_batch_results)
            self.results.create_address_index(conn)
            self.on_search_end(self.SEARCH_TYPE_VALUE)

    def search_memory_operation(self, operation, args=None):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        self.on_search_start(self.SEARCH_TYPE_OPERATION)
        sv = Value.create("0", self.search_size)
        _batch_results = []
        with self.results.db() as conn:
            def result_callback(results: list):
                self.results.add_results(conn, results)

            regions = self.get_regions()

            for start, stop in regions:
                try:
                    self.check_cancel()
                    i_start = start
                    while True:
                        size = min(stop - i_start, self.max_capture_size)
                        if size <= 0:
                            break
                        region_buffer = (sv.get_ctype() * size)()
                        self.memory.read_memory(i_start, region_buffer)
                        search_buffer = SearchBuffer.create(region_buffer, i_start, sv, result_callback, _batch_results, self.result_write_threshold)
                        sz = search_buffer.find_by_operation(operation, args)
                        if self.progress:
                            self.progress.increment(sz)
                        self.check_cancel()
                        i_start += size
                except OSError:
                    pass
                except BreakException:
                    self.on_search_cancel(self.SEARCH_TYPE_OPERATION)
                    raise
            if len(_batch_results) > 0:
                result_callback(_batch_results)
            self.results.create_address_index(conn)
            self.on_search_end(self.SEARCH_TYPE_OPERATION)


    def _search_continue_value_results(self, sv: Value):
        if sv.get_store_type() == 'array':
            op = EqualArray(AOBValue(sv.get_printable()).aob_item['aob_bytes'])
        elif sv.get_store_type() == 'float':
            op = EqualFloat(sv.get())
        else:
            op = EqualInt(sv.get())
        self._search_continue_operation_result(op, store_size=sv.get_store_size())

    def search_continue_value(self, value: str):
        if self.results is None or len(self.results) == 0:
            self.search_memory_value(value)
            return
        self.on_search_start(self.SEARCH_TYPE_CONTINUE)
        sv = Value.create(value, self.search_size)
        self.signed = sv.is_signed() if isinstance(sv, IntValue) else False
        try:
            self._search_continue_value_results(sv)
        except BreakException:
            self.on_search_cancel(self.SEARCH_TYPE_CONTINUE)
            raise
        self.on_search_end(self.SEARCH_TYPE_CONTINUE)


    def _search_continue_operation_result(self, operation: Operation, store_size=4):
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        _update_list = []
        read_counter = 0
        with self.results.db() as conn:
            for (addr, data) in self.results.get_results(conn, table_name=self.results.table_stack[-2]):
                try:
                    prev = sv.from_bytes(data)
                    read = sv.read_bytes_from_memory(self.memory, addr)
                    if operation.operation(sv.from_bytes(read), prev):
                        _update_list.append((addr, read))
                    if len(_update_list) >= self.result_write_threshold:
                        self.results.add_results(conn, _update_list)
                        _update_list.clear()
                    read_counter += 1
                    if read_counter % self.result_progress_threshold == 0:
                        if self.progress:
                            self.progress.increment(self.result_progress_threshold)
                        self.check_cancel()
                except OSError:
                    pass
            if len(_update_list) > 0:
                self.results.add_results(conn, _update_list)

    def _search_continue_capture_operation(self, operation: MemoryOperation, store_size=4):
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        _batch_results = []
        with self.results.db() as conn:
            def result_callback(results: list):
                self.results.add_results(conn, results)
            for f in self.capture_files:
                parts = f.stem.split('_')
                start = int(parts[1], 16)
                stop = int(parts[2], 16)
                cap_file = f
                try:
                    self.check_cancel()
                    read_bytes = cap_file.read_bytes()
                    capture_buffer = (sv.get_ctype() * len(read_bytes))()
                    ctypes.memmove(ctypes.pointer(capture_buffer), read_bytes, len(read_bytes))
                    region_buffer = (sv.get_ctype() * (stop - start))()
                    self.memory.read_memory(start, region_buffer)
                    search_buffer = SearchBuffer.create(region_buffer, start, sv, result_callback, _batch_results, self.result_write_threshold)
                    compare_buffer = SearchBuffer.create(capture_buffer, start, sv, result_callback, result_write_threshold=self.result_write_threshold)
                    count = search_buffer.compare_by_operation(compare_buffer, operation)
                    if self.progress:
                        self.progress.increment(count)
                except OSError:
                    if self.progress:
                        self.progress.increment(stop-start)
                    continue
            if len(_batch_results) > 0:
                result_callback(_batch_results)
            self.results.create_address_index(conn)

    def search_continue_operation(self, operation: Operation):
        if self.last_search_type == Searcher.SEARCH_RETURN_RESULT: #we will do a continuation of a result search
            self.on_search_start(self.SEARCH_TYPE_CONTINUE)
            with self.results.db() as conn:
                store_size = self.results.get_store_size(conn)
            try:
                self._search_continue_operation_result(operation, store_size=store_size)
            except BreakException:
                self.on_search_cancel(self.SEARCH_TYPE_CONTINUE)
                raise
            self.on_search_end(self.SEARCH_TYPE_CONTINUE)
        elif self.last_search_type == Searcher.SEARCH_RETURN_CAPTURE and len(self.capture_files) > 0: #we will do a capture comparison
            if not isinstance(operation, MemoryOperation):
                raise SearchException('Cannot continue search with this type of operation.')
            self.on_search_start(self.SEARCH_TYPE_COMPARE_CAPTURE)
            try:
                self._search_continue_capture_operation(operation, store_size=self.search_size)
            except BreakException:
                self.on_search_cancel(self.SEARCH_TYPE_COMPARE_CAPTURE)
                raise
            self.on_search_end(self.SEARCH_TYPE_COMPARE_CAPTURE)
        else:
            raise SearchException('Cannot continue search with no results or capture files')
        self.last_search_type = Searcher.SEARCH_RETURN_RESULT


    def cancel(self):
        self.cancel_search = True

    def get_cancel(self):
        return self.cancel_search

    def check_cancel(self):
        if self.cancel_search:
            self.cancel_search = False
            raise BreakException()


    def delete_captures(self):
        for res in self.capture_files:
            res.unlink(missing_ok=True)
        self.capture_files.clear()

    def delete_previous_results_and_captures(self):
        for res in self.capture_files:
            res.unlink(missing_ok=True)
        self.capture_files.clear()
        if self.results is not None:
            with self.results.db() as conn:
                self.results.clear_results(conn)

    def get_results(self, limit=-1):
        if self.results is None:
            return []
        with self.results.db() as conn:
            return [{'address': x[0], 'value': x[1]} for x in self.results.get_results(conn, _count=limit)]

    def reset(self):
        if self.progress:
            self.progress.reset()
        self.delete_previous_results_and_captures()
        self.delete_captures()

