import copy
import ctypes
import logging
import traceback
from threading import Thread, Lock, Event
from typing import Union

from falcon import Request, Response
from falcon.app_helpers import MEDIA_JSON

from app.helpers import DynamicHTML, MemoryHandler, Progress
from app.helpers import memory_utils
from app.helpers.exceptions import SearchException, BreakException
from app.search.operations import GreaterThan, LessThan, GreaterThanFloat, LessThanFloat, IncreaseOperation, \
    DecreaseOperation, \
    IncreaseOperationFloat, DecreaseOperationFloat, ChangedOperation, UnchangedOperation, ChangedOperationFloat, \
    UnchangedOperationFloat, ChangedByOperation, ChangedByOperationFloat
from app.search.searcher import Searcher
from app.search.searcher_multi import SearcherMulti
from app.search.value import Value

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]


class Search(MemoryHandler):
    FLOW_START = 4
    FLOW_SEARCHING = 6
    FLOW_RESULTS = 0
    FLOW_NO_RESULTS = 2
    FLOW_INITIALIZE_UNKNOWN = 1
    def __init__(self):
        super().__init__('search')
        self.handle_map = {
            "SEARCH_INITIALIZE": self.handle_initialization,
            "SEARCH_RESULT_UPDATE": self.handle_result_update,
            "SEARCH_RESET": self.handle_reset,
            "SEARCH_START": self.handle_search,
            "SEARCH_STATUS": self.handle_initialization,
            "SEARCH_WRITE": self.handle_write,
            "SEARCH_FREEZE": self.handle_freeze
        }
        self.search_map = {
            'equal_to': self._equal_search,
            'greater_than': self._greater_search,
            'less_than': self._lesser_search,
            'unknown': self._unknown_search,
            'unknown_near': self._unknown_near_search,
            'increase': self._increase_search,
            'decrease': self._decrease_search,
            'changed': self._changed_search,
            'unchanged': self._unchanged_search,
            'changed_by': self._changed_by_search
        }
        self.flow = self.FLOW_START
        self.type = ""
        self.size = ""
        self.value: Value = None
        self.searcher: SearcherMulti = None


        self.search_thread: Thread = None
        self.update_thread: Search.UpdateThread = None

        self.previous_stats = {'results': [], 'flow': self.FLOW_START, 'round': 0}
        self.round = 0
        self.progress = Progress()

    def kill(self):
        if self.search_thread and self.search_thread.is_alive():
            self.searcher.cancel()
            self.search_thread.join()
        self.stop_updater()


    def release(self):
        self.reset()

    def process_error(self, msg: str):
        self.reset()

    def set(self, data):
        self.round = 0
        pass


    def html_main(self):
        return DynamicHTML('resources/search.html', 1).get_html()

    def reset(self):
        if self.search_thread and self.search_thread.is_alive():
            self.searcher.cancel()
            self.search_thread.join()
        self.stop_updater()
        self.searcher.reset()
        self.round = 0
        self.type = ""
        self.size = ""
        self.value = None
        self.search_thread: Thread = None
        self.update_thread: Search.UpdateThread = None
        self.previous_stats = {'results': [], 'flow': self.FLOW_START, 'round': 0}
        self.flow = self.FLOW_START



    def handle_initialization(self, req: Request, resp: Response):
        if self.flow == self.FLOW_START:
            if self.type:
                resp.media['type'] = self.type
            if self.size:
                resp.media['size'] = self.size
            if self.value:
                resp.media['value'] = str(self.value.get_printable())
        elif self.flow == self.FLOW_SEARCHING:
            resp.media['progress'] = self.progress.get_progress() if self.progress else 0
            resp.media['repeat'] = 1000
            resp.media['round'] = self.round
            resp.media['results'] = []
            resp.media['count'] = 0
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = str(self.value.get_printable())
        elif self.flow == self.FLOW_RESULTS:
            resp.media['round'] = self.round
            resp.media['results'] = self.get_updated_addresses()
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = str(self.value.get_printable()) if self.is_value_search() else "0"
            resp.media['count'] = len(self.searcher.results)
            resp.media['repeat'] = 0


    def handle_reset(self, req: Request, resp: Response):
        if self.flow == self.FLOW_SEARCHING: #we are stopping
            self.searcher.cancel()
            self.search_thread.join()
            if not self.searcher.get_cancel(): #was cancellation successful:
                self.round = self.previous_stats['round']
                self.flow = self.previous_stats['flow']
                resp.media['results'] = self.get_updated_addresses()
                resp.media['round'] = self.round
                resp.media['type'] = self.type
                resp.media['size'] = self.size
                resp.media['value'] = str(self.value.get())
                resp.media['count'] = len(self.searcher.results)
                if self.flow == self.FLOW_RESULTS:
                    self.stop_updater()
                    self.start_updater()
        else:
            if self.type in ['increase', 'decrease', 'unchanged', 'changed', 'changed_by']:
                self.type = 'equal_to'
            self.stop_updater()
            self.flow = self.FLOW_START
            resp.media['results'] = []
            self.round = 0
            self.value = None
            self.size = 'byte_4'
            resp.media['round'] = self.round
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = ""
            resp.media['count'] = 0
            self.reset()

    def handle_search(self, req: Request, resp: Response):
        if self.search_thread and self.search_thread.is_alive():
            self.memory.break_search()
            self.search_thread.join()
        self.stop_updater()
        self.type = req.media['type']
        self.size = req.media['size']
        sv = req.media['value'] if self.is_value_search() and len(req.media['value']) > 0 else "0"
        self.value = Value.create(sv, req.media['size'])
        resp.media['type'] = self.type
        resp.media['size'] = self.size
        resp.media['value'] = self.value.get_printable()
        if req.media['type'] not in self.search_map:
            if self.round == 0:
                self.flow = self.FLOW_START
            raise SearchException("Search type {} is not valid".format(req.media['type']))
        if not self.searcher:
            self.searcher = SearcherMulti(self.mem(), self.progress)
            self.searcher.reset()
        search_op = self.search_map[req.media['type']]
        self.search_thread = Thread(target=self._search, args=[search_op])
        self.previous_stats['flow'] = self.flow
        self.previous_stats['round'] = self.round
        self.previous_stats['results'] = None
        self.flow = self.FLOW_SEARCHING
        resp.media['progress'] = 0
        resp.media['repeat'] = 400
        resp.media['round'] = 0
        resp.media['results'] = []
        resp.media['count'] = 0
        self.search_thread.start()

    def handle_write(self, req: Request, resp: Response):
        if not self.update_thread or not self.update_thread.is_alive():
            raise SearchException("Update thread not running. Can't write value.")
        try:
            addr = int(req.media['address'])
            value = Value.create(req.media['value'], self.value.get_store_type())
            self.update_thread.write(addr, value)
        except Exception:
            raise SearchException("Address or value is not valid for write.")
        finally:
            resp.media['round'] = self.round
            resp.media['results'] = self.get_updated_addresses()
            resp.media['count'] = len(self.searcher.results)
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = str(self.value.get())


    def handle_freeze(self, req: Request, resp: Response):
        if not self.update_thread or not self.update_thread.is_alive():
            raise SearchException("Update thread not running. Can't freeze value.")
        try:
            addr = int(req.media['address'])
            tp = memory_utils.typeToCType[(self.size, False)]
            if self.size == 'array':
                tp = (tp * memory_utils.aob_size(self.value.get_printable(), wildcard=True))
            val = self.mem().read_memory(addr, tp())
            freeze = req.media['freeze'] == 'true'
            self.update_thread.freeze(addr, val, freeze)
        except Exception:
            traceback.print_exc()
            raise SearchException("Address or value is not valid for write.")
        finally:
            resp.media['round'] = self.round
            resp.media['results'] = self.get_updated_addresses()
            resp.media['count'] = len(self.searcher.results)
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = str(self.value.get())

    def handle_result_update(self, req: Request, resp: Response):
        if not self.update_thread or not self.update_thread.is_alive():
            resp.media['repeat'] = 0
            resp.media['array'] = False
            resp.media['count'] = 0
            resp.media['results'] = []
        else:
            resp.media['results'] = self.get_updated_addresses()
            resp.media['array'] = isinstance(self.update_thread.parsed_value, ctypes.Array)
            resp.media['count'] = len(self.searcher.results)
            resp.media['repeat'] = 1000

    def get_updated_addresses(self):
        if not self.update_thread:
            res = self.searcher.get_results(limit=40)
            Search.UpdateThread.results_to_update(self.size, res)
            return res
        return self.update_thread.get_addresses()


    def process(self, req: Request, resp: Response):
        resp.media = {}
        command = req.media['command']
        assert (command in self.handle_map)
        resp.content_type = MEDIA_JSON
        try:
            self.handle_map[command](req, resp)
        except SearchException as e:
            resp.media['error'] = e.get_message()
        finally:
            resp.media['flow'] = self.flow


    def _search(self, searcher):
        self.stop_updater()
        try:
            searcher(copy.deepcopy(self.value))
        except BreakException:
            return
        except SearchException:
            self._search_error()
            return
        self._search_complete()

    def _search_complete(self):
        self.round += 1
        if self.searcher.has_results():
            if len(self.searcher.results) > 0:
                self.start_updater()
                self.flow = self.FLOW_RESULTS
            else:
                self.stop_updater()
                self.flow = self.FLOW_NO_RESULTS
        elif self.searcher.has_captures():
            self.flow = self.FLOW_INITIALIZE_UNKNOWN
        else:
            self.flow = self.FLOW_NO_RESULTS

    def _search_error(self):
        self.round += 1
        self.flow = self.FLOW_NO_RESULTS


    def _equal_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if self.searcher.has_results():
            self.searcher.search_continue_value(str(value.get()))
        else:
            self.searcher.search_memory_value(str(value.get()))

    def _greater_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = GreaterThanFloat(value.get())
        else:
            op = GreaterThan(value.get())
        if self.searcher.has_results():
            self.searcher.search_continue_operation(op)
        else:
            self.searcher.search_memory_operation(op)

    def _lesser_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = LessThanFloat(value.get())
        else:
            op = LessThan(value.get())
        if self.searcher.has_results():
            self.searcher.search_continue_operation(op)
        else:
            self.searcher.search_memory_operation(op)

    def _unknown_search(self, value: Value):
        self.searcher.setup_by_value(value)
        self.searcher.capture_memory()

    def _unknown_near_search(self, value: Value):
        self.searcher.setup_by_value(value)
        self.searcher.capture_memory_range(value.get(), 0x100000)

    def _increase_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = IncreaseOperationFloat()
        else:
            op = IncreaseOperation()
        if self.searcher.has_results() or self.searcher.has_captures():
            self.searcher.search_continue_operation(op)
        else:
            self.searcher.search_memory_operation(op)

    def _decrease_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = DecreaseOperationFloat()
        else:
            op = DecreaseOperation()
        if self.searcher.has_results() or self.searcher.has_captures():
            self.searcher.search_continue_operation(op)
        else:
            self.searcher.search_memory_operation(op)

    def _changed_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = ChangedOperationFloat()
        elif value.get_store_type() == 'array':
            op = ChangedOperation()
        else:
            op = ChangedOperation()
        if self.searcher.has_results() or self.searcher.has_captures():
            self.searcher.search_continue_operation(op)
        else:
            raise SearchException("Invalid search")

    def _unchanged_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = UnchangedOperationFloat()
        elif value.get_store_type() == 'array':
            op = UnchangedOperation()
        else:
            op = UnchangedOperation()
        if self.searcher.has_results() or self.searcher.has_captures():
            self.searcher.search_continue_operation(op)
        else:
            raise SearchException("Invalid search")

    def _changed_by_search(self, value: Value):
        self.searcher.setup_by_value(value)
        if value.get_store_type() == 'float':
            op = ChangedByOperationFloat(value.get())
        else:
            op = ChangedByOperation(value.get())
        if self.searcher.has_results() or self.searcher.has_captures():
            self.searcher.search_continue_operation(op)
        else:
            raise SearchException("Invalid search")

    def is_done(self):
        if self.search_thread and self.search_thread.is_alive():
            return False
        return True

    def is_value_search(self):
        if self.type == 'equal_to' or self.type == 'greater_than' or self.type == 'less_than' or self.type == 'changed_by' or self.type == 'unknown_near':
            return True
        return False

    def start_updater(self):
        self.stop_updater()
        self.update_thread = Search.UpdateThread(self.mem(), self.searcher.get_results(40), copy.deepcopy(self.value), self.searcher)
        self.update_thread.start()

    def stop_updater(self):
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.stop.set()
            self.update_thread.join()
        self.update_thread = None

    class UpdateThread(Thread):
        def __init__(self, mem, addrs, pv: Value, s: Searcher):
            super().__init__(target=self.process)
            self.memory = mem
            self.stop = Event()
            self.addresses = copy.deepcopy(addrs)
            self.parsed_value = Value.copy(pv, _signed=s.signed)
            self.results_to_update(pv.get_store_type(), self.addresses)
            self.lock = Lock()
            self.write_list = []
            self.freeze_map = {}
            self.error = ""

        @classmethod
        def results_to_update(cls, size, results):
            if size == 'array':
                for i in range(0, len(results)):
                    v = results[i]
                    byte_str = ' '.join(memory_utils.bytes_to_aob(v))
                    results[i]['value'] = byte_str
            else:
                for v in results:
                    v['value'] = memory_utils.bytes_to_printable_value(v['value'], size)


        def _loop(self):
            try:
                while not self.stop.is_set():
                    self.lock.acquire()
                    if len(self.write_list) > 0:
                        for item in self.write_list:
                            val: Value = item[1]
                            val.write_bytes_to_memory(self.memory, item[0])
                        self.write_list.clear()
                    if len(self.freeze_map) > 0:
                        for addr, value in self.freeze_map.items():
                            self.memory.write_memory(addr, value)
                    for i in range(0, len(self.addresses)):
                        addr = self.addresses[i]
                        self.parsed_value.read_memory(self.memory, addr['address'])
                        self.addresses[i]['value'] = self.parsed_value.get_printable()
                    self.lock.release()
                    self.stop.wait(1)
            except Exception as e:
                self.error = str(e)
            finally:
                self.freeze_map.clear()
                if self.lock.locked():
                    self.lock.release()

        def process(self):
            try:
                self._loop()
            except Exception as e:
                logging.error("Lost Update Thread {}".format(str(e)))
                traceback.print_exc()
                self.error = "Could not update process.  Did it close?"

        def get_addresses(self):
            self.lock.acquire()
            res = copy.deepcopy(self.addresses)
            self.lock.release()
            return res

        def write(self, address, value):
            self.lock.acquire()
            self.write_list.append((address, value))
            self.lock.release()

        def freeze(self, address, value, freeze):
            self.lock.acquire()
            if not freeze and address in self.freeze_map:
                del self.freeze_map[address]
            elif freeze and address not in self.freeze_map:
                self.freeze_map[address] = value
            self.lock.release()


