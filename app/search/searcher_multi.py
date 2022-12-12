import ctypes
import logging
import logging.handlers
import multiprocessing
import os
import traceback
from typing import Union

from mem_edit import Process

from app.helpers.aob_value import AOBValue
from app.helpers.directory_utils import memory_directory
from app.helpers.exceptions import SearchException, BreakException
from app.helpers.progress import Progress
from app.helpers.search_results import SearchResults
from app.helpers.timer import PollTimer
from app.search.buffer import SearchBuffer
from app.search.operations import Operation, MemoryOperation, EqualInt, EqualFloat, EqualArray
from app.search.searcher import Searcher
from app.search.value import Value, IntValue

logger = multiprocessing.log_to_stderr()
#logger.setLevel(multiprocess.SUBDEBUG)


ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class SearcherMulti(Searcher):
    def __init__(self, memory: Process, progress: Progress = None, write_only=True, directory=memory_directory):
        super().__init__(memory, progress, write_only, directory)
        self.multiprocessing_event = None
        multiprocessing.set_start_method('spawn', force=True)
        self.max_capture_size = int((25600000 / 4) * (4 / multiprocessing.cpu_count()))
        self.round_robin_size = 4000000

    def check_multi_clear(self):
        if self.multiprocessing_event.is_set():
            raise BreakException

    def _capture_memory_thread(self, args):
        capture_data = args[0]
        queue: multiprocessing.Queue = args[1]
        self.multiprocessing_event = args[2]
        _id = capture_data['id']
        pid = os.getpid()
        cap_file = self.mem_path.joinpath(capture_data['file'])
        size = capture_data['size']
        pos = capture_data['position']
        try:
            region_buffer = (ctypes.c_byte * size)()
            self.memory.read_memory(pos, region_buffer)
            self.check_multi_clear()
        except OSError:
            queue.put({"pid": pid, "size": size, "filename": None})
            return 0
        with open(cap_file, 'wb') as f:
            f.write(bytes(region_buffer))
        queue.put({"pid": pid, "size": size, "filename": cap_file})
        return 0

    def capture_memory(self):
        self.clear_files()
        self.prepare_memory_search()
        if self.total_size < 500000000:
            super().capture_memory()
            return
        manager = multiprocessing.Manager()
        queue = manager.Queue(maxsize=10000)
        self.cancel_event = manager.Event()
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)
        captures = []
        _id = 0
        for start, stop in self.get_regions():
            size = stop-start
            pos = start
            iterations = [size]
            if size > self.max_capture_size:
                iterations = [self.max_capture_size] * int(size/self.max_capture_size)
                iterations.append(size - int(size/self.max_capture_size) * self.max_capture_size)

            for it in iterations:
                captures.append({'id': _id, 'position': pos, 'start': pos-self.mem_start, 'size':it, 'file': 'capture_{}_{}_{}'.format(pos - self.mem_start, it, _id)})
                _id += 1
                pos += it

        process_args = []
        for cap in captures:
            process_args.append((cap, queue, self.cancel_event))

        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            res = pool.map_async(self._capture_memory_thread, process_args)
            tm = PollTimer(0.5)
            try:
                while True:
                    if tm.has_elapsed():
                        self.check_cancel()
                    if res.ready():
                        done = True
                    else:
                        done = False
                    while not queue.empty():
                        if tm.has_elapsed():
                            self.check_cancel()
                        capture_data = queue.get()
                        if capture_data['filename'] is not None:
                            self.capture_files.append(capture_data['filename'])
                        if self.progress:
                            self.progress.increment(capture_data['size'])
                    if done:
                        res.get()
                        break
                    res.wait(1.0)
            except BreakException:
                pool.terminate()
                pool.join()
                raise BreakException()
            if self.progress:
                self.progress.mark()

    def _search_continue_capture_operation_thread(self, args):
        try:
            cap_file = args['filename']
            queue: multiprocessing.Queue = args['queue']
            self.multiprocessing_event: multiprocessing.Event = args['clear']
            start = args['start']
            stop = args['stop']
            sv = Value.create(args['value']['string'], args['value']['size'])
            _id = args['id']
            operation = args['operation']
            new_results = SearchResults.from_result(self.results, sv.get_store_size())
            new_results.set_name("r_{}_{}".format(_id, os.getpid()))

            def progressCB(delta):
                queue.put({'delta': delta, 'pid': os.getpid()})

            def resultCB(_results: list):
                [new_results.add(res['address'], res['value']) for res in _results]
                _results.clear()

            try:
                read_bytes = cap_file.read_bytes()
                capture_buffer = (sv.get_ctype() * len(read_bytes))(*read_bytes)
                region_buffer = (sv.get_ctype() * (stop - start))()
                self.memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, resultCB, progress_callback=progressCB, cancel_callback=self.check_multi_clear)
                compare_buffer = SearchBuffer.create(capture_buffer, start, sv, resultCB)
                search_buffer.compare_by_operation(compare_buffer, operation)
                queue.put({'pid': os.getpid(), 'complete': True, 'results': new_results})
            except OSError:
                queue.put({'delta': stop-start, 'pid': os.getpid(), 'complete': True, 'os_error': True})
        except Exception as e:
            logger.error(traceback.print_exc())

    def _search_continue_capture_operation(self, operation: MemoryOperation):
        self.prepare_memory_search()
        if self.total_size < 12000000:
            super()._search_continue_capture_operation(operation)
            return
        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*self.results.store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        manager = multiprocessing.Manager()
        queue = manager.Queue(maxsize=10000)
        self.cancel_event = manager.Event()
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)

        process_args = []
        _id = 0
        for f in self.capture_files:
            start = self.mem_start + int(f.parts[-1].split('_')[1])
            stop = start + int(f.parts[-1].split('_')[2])
            cap_file = f
            process_args.append({'filename': cap_file, 'start': start, 'stop': stop, 'value': {'string': sv.raw_value, 'size': self.search_size}, 'queue': queue, 'operation': operation, 'clear': self.cancel_event, 'id': _id})
            _id += 1

        expected_returns = len(process_args)
        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            res = pool.map_async(self._search_continue_capture_operation_thread, process_args)
            try:
                while expected_returns > 0:
                    self.check_cancel()
                    while not queue.empty():
                        self.check_cancel()
                        process_data = queue.get()
                        if 'delta' in process_data:
                            if self.progress:
                                self.progress.increment(process_data['delta'])
                        if 'error' in process_data:
                            print('error', process_data['error'], flush=True)
                        if 'complete' in process_data:
                            expected_returns -= 1
                            self.results.extend(process_data['results'])
                    res.wait(1.0)
            except BreakException:
                pool.terminate()
                pool.join()
                raise BreakException()
            if self.progress:
                self.progress.mark()

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


    def _search_memory_value_thread(self, args):
        queue: multiprocessing.Queue = args['queue']
        self.multiprocessing_event: multiprocessing.Event = args['clear']
        regions = args['cpu']
        sv = Value.create(args['value']['string'], args['value']['size'])
        _id = args['id']
        new_results = SearchResults.from_result(self.results, sv.get_store_size())
        new_results.set_name("r_{}_{}".format(_id, os.getpid()))


        def progressCB(delta):
            queue.put({'delta': delta, 'pid': os.getpid(), 'id': _id})

        def resultCB(_results: list):
            [new_results.add(res['address'], res['value']) for res in _results]
            _results.clear()

        for region in regions:
            start = region['start']
            size = region['size']
            try:
                region_buffer = (sv.get_ctype() * size)()
                self.memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, resultCB, progress_callback=progressCB, cancel_callback=self.check_multi_clear)
                search_buffer.find_value(sv)
            except OSError:
                queue.put({'id': _id, 'delta': size, 'pid': os.getpid(), 'os_error': True})
            except Exception as e:
                queue.put({'id': _id, 'delta': size, 'pid': os.getpid(), 'error': traceback.format_exc()})
        queue.put({'id': _id, 'complete': True, 'res': new_results})

    def search_memory_value(self, value: str):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        self.prepare_memory_search()
        self.delete_previous_results_and_captures()

        sv = Value.create(value, self.search_size)
        self.results.store_size = sv.store_size
        self.signed = sv.is_signed() if isinstance(sv, IntValue) else False
        manager = multiprocessing.Manager()
        queue = manager.Queue(maxsize=10000)
        self.cancel_event = manager.Event()
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)

        process_args = []
        mem_map = self._create_round_robin(sv)

        for i in range(0, len(mem_map)):
            process_args.append({'cpu': mem_map[i], 'value': {'string': value, 'size': self.search_size}, 'queue': queue, 'id': i, 'clear': self.cancel_event, 'end_event': manager.Event()})
        expected_returns = list(range(0, len(process_args)))
        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            res = pool.map_async(self._search_memory_value_thread, process_args)
            tm = PollTimer(1)
            try:
                while expected_returns:
                    if tm.has_elapsed():
                        self.check_cancel()
                    while not queue.empty():
                        if tm.has_elapsed():
                            self.check_cancel()
                        process_data = queue.get()
                        if 'delta' in process_data:
                            if self.progress:
                                self.progress.increment(process_data['delta'])
                        if 'error' in process_data:
                            logger.error("{} - {}".format(process_data['id'], process_data['error']))
                        if 'complete' in process_data:
                            expected_returns.remove(process_data['id'])
                            process_args[int(process_data['id'])]['end_event'].set()
                            self.results.extend(process_data['res'])
                    res.wait(1.0)
            except BreakException:
                pool.terminate()
                pool.join()
                raise BreakException()
        if self.progress:
            self.progress.mark()

    def _search_memory_operation_thread(self, args):
        queue: multiprocessing.Queue = args['queue']
        self.multiprocessing_event: multiprocessing.Event = args['clear']
        regions = args['cpu']
        sv = Value.create(args['value']['string'], args['value']['size'])
        _id = args['id']
        operation = args['operation']
        new_results = SearchResults.from_result(self.results, sv.get_store_size())
        new_results.set_name("r_{}_{}".format(_id, os.getpid()))

        def progressCB(delta):
            queue.put({'delta': delta, 'pid': os.getpid()})

        def resultCB(_results):
            [new_results.add(res['address'], res['value']) for res in _results]
            _results.clear()

        for region in regions:
            start = region['start']
            size = region['size']
            try:
                region_buffer = (sv.get_ctype() * size)()
                self.memory.read_memory(start, region_buffer)
                search_buffer = SearchBuffer.create(region_buffer, start, sv, resultCB, progress_callback=progressCB, cancel_callback=self.check_multi_clear)
                search_buffer.find_by_operation(operation, args)
            except OSError:
                queue.put({'id': _id, 'delta': size, 'pid': os.getpid(), 'os_error': True})
            except Exception as e:
                queue.put({'id': _id, 'delta': size, 'pid': os.getpid(), 'error': traceback.format_exc()})
        queue.put({'id': _id, 'complete': True, 'res': new_results})

    def search_memory_operation(self, operation, args=None):
        if self.results is None:
            raise SearchException('No results associated with the searcher')
        self.prepare_memory_search()
        self.delete_previous_results_and_captures()
        sv = Value.create("0", self.search_size)
        self.results.store_size = sv.store_size
        try:
            manager = multiprocessing.Manager()
        except Exception as e:
            return
        queue = manager.Queue(maxsize=10000)

        self.cancel_event = manager.Event()
        if self.progress:
            self.progress.add_constraint(0, self.total_size, 1.0)

        process_args = []
        mem_map = self._create_round_robin(sv)

        for i in range(0, len(mem_map)):
            process_args.append({'cpu': mem_map[i], 'value': {'string': "0", "size": self.search_size}, 'operation': operation, 'queue': queue, 'id': i, 'clear': self.cancel_event, 'end_event': manager.Event()})

        expected_returns = list(range(0, len(process_args)))
        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            res = pool.map_async(self._search_memory_operation_thread, process_args, chunksize=1)
            tm = PollTimer(1)
            try:
                while expected_returns:
                    if tm.has_elapsed():
                        self.check_cancel()
                    while not queue.empty():
                        if tm.has_elapsed():
                            self.check_cancel()
                        process_data = queue.get()
                        if 'delta' in process_data:
                            logging.getLogger(__name__).info('delta {}'.format(process_data['delta']))
                            if self.progress:
                                self.progress.increment(process_data['delta'])
                        if 'error' in process_data:
                            logging.getLogger(__name__).error(process_data['error'])
                        if 'complete' in process_data:
                            expected_returns.remove(process_data['id'])
                            process_args[int(process_data['id'])]['end_event'].set()
                            self.results.extend(process_data['res'])
                    res.wait(1.0)
            except BreakException:
                pool.terminate()
                pool.join()
                raise BreakException()
        if self.progress:
            self.progress.mark()

    def _search_continue_value_results_thread(self, args):
        queue: multiprocessing.Queue = args['queue']
        start = args['start']
        self.multiprocessing_event: multiprocessing.Event = args['clear']
        size = args['size']
        sv = Value.create(args['value']['string'], args['value']['size'])
        op = args['operation']
        new_results = SearchResults.from_result(self.results, sv.get_store_size())

        try:
            count = 0
            last = 0
            for res in self.results[start:start+size]:
                addr = res['address']
                try:
                    read = sv.read_bytes_from_memory(self.memory, addr)
                    if op.operation(sv.from_bytes(read)):
                        res['value'] = read
                        new_results.add_r(res)
                except OSError:
                    pass
                count += 1
                if count % 1000 == 0:
                    queue.put({'delta': 1000, 'pid': os.getpid()})
                    last = count
                    self.check_multi_clear()
            queue.put({'results': new_results, 'pid': os.getpid(), 'complete': True, 'delta': count-last})
        except Exception as e:
            queue.put({'delta': size, 'pid': os.getpid(), 'error': traceback.format_exc(), 'complete': True})

    def _search_continue_value_results(self, sv: Value):
        if len(self.results) < 1000:
            super()._search_continue_value_results(sv)
            return

        if sv.get_store_type() == 'array':
            op = EqualArray(AOBValue(sv.get_printable()).aob_item['aob_bytes'])
        elif sv.get_store_type() == 'float':
            op = EqualFloat(sv.get())
        else:
            op = EqualInt(sv.get())
        new_results = SearchResults.from_result(self.results, sv.get_store_size())

        manager = multiprocessing.Manager()
        queue = manager.Queue(maxsize=10000)
        self.cancel_event = manager.Event()
        processes = max(1, multiprocessing.cpu_count() - 1)
        segments = int(len(self.results) / processes)
        if self.progress:
            self.progress.add_constraint(0, len(self.results), 1.0)

        process_args = []
        start = 0

        for i in range(0, processes):
            size = segments
            if i == processes-1:
                size = len(self.results) - start
            process_args.append({'start': start, 'size': segments, 'value': {"string": sv.raw_value, "size": self.search_size}, 'queue': queue, 'operation': op, 'clear': self.cancel_event})
            start += size

        expected_returns = len(process_args)
        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            res = pool.map_async(self._search_continue_value_results_thread, process_args, chunksize=1)
            tm = PollTimer(1)
            try:
                while expected_returns > 0:
                    if tm.has_elapsed():
                        self.check_cancel()
                    while not queue.empty():
                        if tm.has_elapsed():
                            self.check_cancel()
                        process_data = queue.get()
                        if 'delta' in process_data:
                            logging.getLogger(__name__).info('delta {}'.format(process_data['delta']))
                            if self.progress:
                                self.progress.increment(process_data['delta'])
                        if 'results' in process_data:
                            new_results.extend(process_data['results'])
                        if 'error' in process_data:
                            logging.getLogger(__name__).error(process_data['error'])
                        if 'complete' in process_data:
                            expected_returns -= 1
                    res.wait(1.0)
            except BreakException:
                pool.terminate()
                pool.join()
                raise BreakException()
        self.results = new_results


    def _search_continue_operation_results_thread(self, args):
        queue: multiprocessing.Queue = args['queue']
        start = args['start']
        size = args['size']
        sv = Value.create(args['value']['string'], args['value']['size'])
        operation = args['operation']
        self.multiprocessing_event: multiprocessing.Event = args['clear']
        new_results = SearchResults.from_result(self.results, sv.get_store_size())

        try:
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
            count = 0
            last = 0
            res_list = self.results[start:start+size]
            for res in res_list:
                if run_op(res):
                    new_results.add_r(res)
                count += 1
                if count % 1000 == 0:
                    queue.put({'delta': 1000, 'pid': os.getpid()})
                    last = count
                    self.check_multi_clear()
            queue.put({'results': new_results, 'pid': os.getpid(), 'complete': True, 'delta': count-last})
        except Exception as e:
            queue.put({'delta': size, 'pid': os.getpid(), 'error': traceback.format_exc(), 'complete': True})


    def _search_continue_operation_result(self, operation: Operation):
        if len(self.results) < 1000:
            super()._search_continue_operation_result(operation)
            return

        if self.search_size == 'array':
            sv = Value.create(" ".join(["00"]*self.results.store_size), self.search_size)
        else:
            sv = Value.create("0", self.search_size)
            if isinstance(sv, IntValue):
                sv.set_signed(self.signed)
        new_results = SearchResults.from_result(self.results, sv.get_store_size())
        manager = multiprocessing.Manager()
        queue = manager.Queue(maxsize=10000)
        processes = max(1, multiprocessing.cpu_count() - 1)
        segments = int(len(self.results) / processes)

        process_args = []
        start = 0
        if self.progress:
            self.progress.add_constraint(0, len(self.results), 1.0)


        for i in range(0, processes):
            size = segments
            if i == processes-1:
                size = len(self.results) - start
            process_args.append({'start': start, 'size': segments, 'value': {"string": sv.raw_value, "size": self.search_size}, 'queue': queue, 'operation': operation, 'clear': self.cancel_event})
            start += size
        expected_returns = len(process_args)
        with multiprocessing.Pool(processes=max(1, multiprocessing.cpu_count() - 1)) as pool:
            res = pool.map_async(self._search_continue_operation_results_thread, process_args, chunksize=1)
            tm = PollTimer(1)
            try:
                while expected_returns > 0:
                    if tm.has_elapsed():
                        self.check_cancel()
                    while not queue.empty():
                        if tm.has_elapsed():
                            self.check_cancel()
                        process_data = queue.get()
                        if 'delta' in process_data:
                            logging.getLogger(__name__).info('delta {}'.format(process_data['delta']))
                            if self.progress:
                                self.progress.increment(process_data['delta'])
                        if 'results' in process_data:
                            new_results.extend(process_data['results'])
                        if 'error' in process_data:
                            logging.getLogger(__name__).error(process_data['error'])
                        if 'complete' in process_data:
                            expected_returns -= 1
                    res.wait(1.0)
            except BreakException:
                pool.terminate()
                pool.join()
                raise BreakException()
        self.results = new_results










