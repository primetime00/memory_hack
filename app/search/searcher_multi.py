import ctypes
import multiprocessing
import os
import platform
import traceback
from typing import Union

from mem_edit import Process

from app.helpers.aob_value import AOBValue
from app.helpers.directory_utils import memory_directory
from app.helpers.exceptions import SearchException, BreakException
from app.helpers.progress import Progress
from app.helpers.search_results import SearchResults
from app.search.buffer import SearchBuffer
from app.search.operations import Operation, MemoryOperation, EqualInt, EqualFloat, EqualArray
from app.search.searcher import Searcher
from app.search.value import Value, IntValue

logger = multiprocessing.log_to_stderr()
#logger.setLevel(multiprocess.SUBDEBUG)


ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class SearcherMulti(Searcher):
    def __init__(self, memory: Process, progress: Progress = None, write_only=True, directory=memory_directory, results: SearchResults=None):
        super().__init__(memory, progress, write_only, directory, results)
        self.multiprocessing_event = None
        multiprocessing.set_start_method('spawn', force=True)
        self.round_robin_size = 4096000
        self.single_process = False

    def check_multi_clear(self):
        if self.multiprocessing_event.is_set():
            raise BreakException

    def get_mp_memory(self):
        if platform.system() == "Windows":
            return Process(self.memory.pid)
        return self.memory

    def release_mp_memory(self, proc: Process):
        if platform.system() == "Windows":
            proc.close()

    def set_single_process(self, p):
        self.single_process = p

    def _create_uniform_rounds(self, sv: Value, max_size=40000000):
        mem_map = {0: []}
        current_size = max_size
        region_index = 0
        region_list = list(self.get_regions())
        for ri in range(0, len(region_list)):
            region = region_list[ri]
            current_start = region[0]
            while True:
                size = region[1]-current_start
                if current_size - size <= 0: #next worker
                    size = current_size
                    size -= (size % sv.store_size)
                    mem_map[region_index].append({'region_index': region_index, 'start': current_start, 'size': size})
                    region_index += 1
                    mem_map[region_index] = []
                    current_start += size
                    current_size = max_size
                elif current_size - size > 0: #next region
                    if size > 0:
                        mem_map[region_index].append({'region_index': region_index, 'start': current_start, 'size': size})
                    else:
                        del mem_map[region_index]
                    current_size -= size
                    break
                else:
                    size = current_size
                    mem_map[region_index].append({'region_index': region_index, 'start': current_start, 'size': size})
                    region_index += 1
                    mem_map[region_index] = []
                    current_size = max_size
                    break
        return mem_map

    def _create_round_robin(self, sv: Value):
        cpus = max(1, multiprocessing.cpu_count() - 1)
        mem_map = {}
        for i in range(0, cpus):
            mem_map[i] = []
        region_list = list(self.get_regions())
        current_size = self.round_robin_size
        cpu_index = 0
        for ri in range(0, len(region_list)):
            region = region_list[ri]
            current_start = region[0]
            while True:
                size = region[1]-current_start
                if current_size - size <= 0: #next cpu
                    size = current_size
                    size -= (size % sv.store_size)
                    mem_map[cpu_index].append({'cpu': cpu_index, 'start': current_start, 'size': size})
                    cpu_index += 1
                    cpu_index %= cpus
                    current_start += size
                    current_size = self.round_robin_size
                elif current_size - size > 0: #next region
                    mem_map[cpu_index].append({'cpu': cpu_index, 'start': current_start, 'size': size})
                    current_size -= size
                    break
                else:
                    size = current_size
                    mem_map[cpu_index].append({'cpu': cpu_index, 'start': current_start, 'size': size})
                    cpu_index += 1
                    cpu_index %= cpus
                    current_size = self.round_robin_size
                    break
        return mem_map



    def _capture_memory_thread(self, args):
        capture_data = args[0]
        pid = os.getpid()
        cap_file = self.mem_path.joinpath(capture_data['file'])
        size = capture_data['size']
        pos = capture_data['position']
        memory = self.get_mp_memory()
        try:
            region_buffer = (ctypes.c_byte * size)()
            memory.read_memory(pos, region_buffer)
            self.release_mp_memory(memory)
        except OSError:
            return {"pid": pid, "size": size, "filename": cap_file, "error": True}
        with open(cap_file, 'wb') as f:
            f.write(bytes(region_buffer))
        return {"pid": pid, "size": size, "filename": cap_file, "error": False}

    def capture_memory(self):
        if self.total_size < 500000000 or self.single_process:
            super().capture_memory()
            return
        self.on_search_start(self.SEARCH_TYPE_CAPTURE)
        captures = []
        for start, stop in self.get_regions():
            size = stop-start
            pos = start
            iterations = [size]
            if size > self.max_capture_size:
                iterations = [self.max_capture_size] * int(size/self.max_capture_size)
                iterations.append(size - int(size/self.max_capture_size) * self.max_capture_size)

            for it in iterations:
                captures.append({'position': pos, 'size': it, 'file': 'capture_{:016X}_{:016X}.cap'.format(pos, pos+it)})
                pos += it

        process_args = []
        for cap in captures:
            process_args.append((cap,))
        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            try:
                for res in pool.imap_unordered(self._capture_memory_thread, process_args, chunksize=100):
                    self.check_cancel()
                    if self.progress:
                        self.progress.increment(res['size'])
                    self.capture_files.append(res['filename'])
            except BreakException:
                pool.terminate()
                pool.join()
                self.on_search_cancel(self.SEARCH_TYPE_CAPTURE)
                raise
        self.on_search_end(self.SEARCH_TYPE_CAPTURE)

    def _search_continue_capture_operation_thread(self, args):
        files = args['files']
        sv = Value.create(args['value']['string'], args['value']['size'])
        _id = args['id']
        operation = args['operation']
        results = []
        total_read = 0
        memory = self.get_mp_memory()

        for cap_file, start, stop in files:
            try:
                read_bytes = cap_file.read_bytes()
                capture_buffer = (sv.get_ctype() * len(read_bytes))()
                ctypes.memmove(ctypes.pointer(capture_buffer), read_bytes, len(read_bytes))
                region_buffer = (sv.get_ctype() * (stop - start))()
                memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, _results=results, aligned=self.aligned)
                compare_buffer = SearchBuffer.create(capture_buffer, start, sv, aligned=self.aligned)
                search_buffer.compare_by_operation(compare_buffer, operation)
                total_read += len(read_bytes)
            except OSError as e1:
                continue
            except Exception as e:
                self.release_mp_memory(memory)
                return {'id': _id, 'results': [], 'count': 0, 'error': traceback.format_exc()}
        self.release_mp_memory(memory)
        return {'id': _id, 'results': results, 'count': total_read}

    def _search_continue_capture_operation(self, operation: MemoryOperation, store_size=4):
        if self.total_size < 12000000 or self.single_process:
            super()._search_continue_capture_operation(operation)
            return
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)

        process_args = []
        _id = 0
        #max_size = int(self.total_size / (multiprocessing.cpu_count()-1))+4096 #self.max_capture_size
        max_size = 10000000
        current_size = max_size
        files = []

        for f in sorted(self.capture_files, key=lambda x: x.stat().st_size):
            parts = f.stem.split('_')
            start = int(parts[1], 16)
            stop = int(parts[2], 16)
            size = stop-start
            cap_file = f
            if size >= max_size:
                if len(files) > 0:
                    process_args.append({'files': files, 'value': {'string': sv.raw_value, 'size': self.search_size}, 'operation': operation, 'id': _id})
                    _id += 1
                    files = []
                process_args.append({'files': [(cap_file, start, stop)], 'value': {'string': sv.raw_value, 'size': self.search_size}, 'operation': operation, 'id': _id})
                _id += 1
            elif current_size - size < 0:
                process_args.append({'files': files, 'value': {'string': sv.raw_value, 'size': self.search_size}, 'operation': operation, 'id': _id})
                _id += 1
                files = [(cap_file, start, stop)]
                current_size = max_size - size
            elif current_size - size >= 0:
                files.append((cap_file, start, stop))
                current_size -= size
        if len(files) > 0:
            process_args.append({'files': files, 'value': {'string': sv.raw_value, 'size': self.search_size}, 'operation': operation, 'id': _id})

        with self.results.db() as conn:
            with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
                try:
                    for res in pool.imap_unordered(self._search_continue_capture_operation_thread, process_args):
                        self.check_cancel()
                        if self.progress:
                            self.progress.increment(res['count'])
                        if 'error' in res:
                            logger.error("{} - {}".format(res['id'], res['error']))
                        else:
                            self.results.add_results(conn, res['results'])
                except BreakException:
                    pool.terminate()
                    pool.join()
                    raise

    def _search_memory_value_thread(self, args):
        regions = args['region']
        sv = Value.create(args['value']['string'], args['value']['size'])
        _id = args['id']
        memory = self.get_mp_memory()
        results = []
        count = 0
        for region in regions:
            start = region['start']
            size = region['size']
            try:
                region_buffer = (sv.get_ctype() * size)()
                memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, _results=results, aligned=self.aligned)
                count += search_buffer.find_value(sv)
            except OSError as e1:
                self.release_mp_memory(memory)
                return {'id': _id, 'results': results, 'count': 0, 'error': e1}
            except Exception as e:
                self.release_mp_memory(memory)
                return {'id': _id, 'results': results, 'count': 0, 'error': traceback.format_exc()}
        self.release_mp_memory(memory)
        return {'id': _id, 'results': results, 'count': count}

    def search_memory_value(self, value: str):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        if self.total_size <= 128000 or self.single_process:
            super().search_memory_value(value)
            return
        self.on_search_start(self.SEARCH_TYPE_VALUE)
        sv = Value.create(value, self.search_size)
        self.signed = sv.is_signed() if isinstance(sv, IntValue) else False

        process_args = []
        mem_map = self._create_uniform_rounds(sv, max_size=self.mem_average)
        for i in range(0, len(mem_map)):
            process_args.append({'region': mem_map[i], 'value': {'string': value, 'size': self.search_size}, 'id': i})
        with self.results.db() as conn:
            with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
                try:
                    for res in pool.imap_unordered(self._search_memory_value_thread, process_args):
                        self.check_cancel()
                        if self.progress:
                            self.progress.increment(res['count'])
                        if 'error' in res:
                            logger.error("{} - {}".format(res['id'], res['error']))
                        else:
                            self.results.add_results(conn, res['results'])
                except BreakException:
                    pool.terminate()
                    pool.join()
                    self.on_search_cancel(self.SEARCH_TYPE_VALUE)
                    raise
            self.results.create_address_index(conn)
            self.on_search_end(self.SEARCH_TYPE_VALUE)

    def _search_memory_operation_thread(self, args):
        regions = args['region']
        sv = Value.create(args['value']['string'], args['value']['size'])
        _id = args['id']
        operation = args['operation']
        results = []
        count = 0
        memory = self.get_mp_memory()

        for region in regions:
            start = region['start']
            size = region['size']
            try:
                region_buffer = (sv.get_ctype() * size)()
                memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, _results=results, aligned=self.aligned)
                count += search_buffer.find_by_operation(operation, args)
            except OSError as e1:
                self.release_mp_memory(memory)
                return {'id': _id, 'results': results, 'count': 0, 'error': e1}
            except Exception as e:
                self.release_mp_memory(memory)
                return {'id': _id, 'results': results, 'count': 0, 'error': traceback.format_exc()}
        self.release_mp_memory(memory)
        return {'id': _id, 'results': results, 'count': count}

    def search_memory_operation(self, operation, args=None):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        if self.total_size <= 128000 or self.single_process:
            super().search_memory_operation(operation, args)
            return
        self.on_search_start(self.SEARCH_TYPE_OPERATION)
        sv = Value.create("0", self.search_size)
        process_args = []
        mem_map = self._create_uniform_rounds(sv, max_size=self.mem_average)

        for i in range(0, len(mem_map)):
            process_args.append({'region': mem_map[i], 'value': {'string': "0", "size": self.search_size}, 'operation': operation, 'id': i})

        with self.results.db() as conn:
            with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
                try:
                    for res in pool.imap_unordered(self._search_memory_operation_thread, process_args):
                        self.check_cancel()
                        if self.progress:
                            self.progress.increment(res['count'])
                        if 'error' in res:
                            logger.error("{} - {}".format(res['id'], res['error']))
                        else:
                            self.results.add_results(conn, res['results'])
                except BreakException:
                    pool.terminate()
                    pool.join()
                    self.on_search_cancel(self.SEARCH_TYPE_OPERATION)
                    raise
            self.results.create_address_index(conn)
            self.on_search_end(self.SEARCH_TYPE_OPERATION)

    def _search_continue_value_results(self, sv: Value):
        with self.results.db() as conn:
            if self.results.get_number_of_results(conn, -2) < 300 or self.single_process:
                super()._search_continue_value_results(sv)
                return

        if sv.get_store_type() == 'array':
            op = EqualArray(AOBValue(sv.get_printable()).aob_item['aob_bytes'])
        elif sv.get_store_type() == 'float':
            op = EqualFloat(sv.get())
        else:
            op = EqualInt(sv.get())
        self._search_continue_operation_result(op, store_size=sv.get_store_size())

    def _search_continue_operation_results_thread(self, args):
        size = args['size']
        sv = Value.create(args['value']['string'], args['value']['size'])
        sv.signed = self.signed
        operation = args['operation']
        input_results = args['results']
        memory = self.get_mp_memory()
        results = []

        try:
            if isinstance(operation, MemoryOperation):
                def run_op(_results):
                    for res in _results:
                        addr = res[0]
                        read = sv.read_bytes_from_memory(memory, addr)
                        prev_value = sv.from_bytes(res[1])
                        op_test = operation.operation(sv.from_bytes(read), prev_value)
                        if op_test:
                            results.append((addr, read))
            else:
                def run_op(_results):
                    for res in _results:
                        addr = res[0]
                        read = sv.read_bytes_from_memory(memory, addr)
                        op_test = operation.operation(sv.from_bytes(read))
                        if op_test:
                            results.append((addr, read))
            run_op(input_results)
            self.release_mp_memory(memory)
            return {'id': args['id'], 'results': results, 'count': size}
        except Exception as e:
            self.release_mp_memory(memory)
            return {'id': args['id'], 'results': results, 'count': 0, 'error': traceback.format_exc()}

    def _search_continue_operation_result(self, operation: Operation, store_size=4):
        with self.results.db() as conn:
            result_count = self.results.get_number_of_results(conn, -2)
        if result_count < 300 or self.single_process:
            super()._search_continue_operation_result(operation)
            return

        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)

        segments = min(10000, int(result_count / (multiprocessing.cpu_count()-1)))
        regions = int(result_count / segments)

        process_args = []

        with self.results.db() as conn:
            results_cursor = self.results.get_results_unordered(conn, -2)
            for i in range(0, regions):
                if i == regions-1:
                    results = results_cursor.fetchall()
                else:
                    results = results_cursor.fetchmany(segments)
                process_args.append({'results': results, 'size': len(results), 'value': {"string": sv.raw_value, "size": self.search_size}, 'operation': operation, 'id': i})
            with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
                try:
                    for res in pool.imap_unordered(self._search_continue_operation_results_thread, process_args):
                        self.check_cancel()
                        if self.progress:
                            self.progress.increment(res['count'])
                        if 'error' in res:
                            logger.error("{} - {}".format(res['id'], res['error']))
                        else:
                            self.results.add_results(conn, res['results'])
                except BreakException:
                    pool.terminate()
                    pool.join()
                    raise











