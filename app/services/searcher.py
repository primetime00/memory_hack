import copy
import ctypes
import logging
import traceback
from threading import Thread, Lock, Event

from falcon import Request, Response
from falcon.app_helpers import MEDIA_JSON

from app.helpers import DynamicHTML, MemoryHandler, DataStore, Progress
from app.helpers import memory_utils
from app.helpers.exceptions import SearchException, BreakException
from app.helpers.search_utils import SearchUtilities


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
            'increase': self._increase_search,
            'decrease': self._decrease_search,
            'changed': self._changed_search,
            'unchanged': self._unchanged_search,
            'changed_by': self._changed_by_search
        }
        self.flow = self.FLOW_START

        self.type = ""
        self.size = ""
        self.value = ""
        self.search_thread: Thread = None
        self.update_thread: Search.UpdateThread = None
        self.search_results = []
        self.previous_stats = {'results': [], 'flow': self.FLOW_START, 'round': 0}
        self.round = 0
        self.error = ""
        self.progress = Progress()

    def kill(self):
        if self.search_thread and self.search_thread.is_alive():
            DataStore().get_operation_control().control_break()
            self.search_thread.join()
        self.stop_updater()


    def release(self):
        self.reset()

    def process_error(self, msg: str):
        self.reset()

    def set(self, data):
        self.round = 0
        pass
        #self.memory.initialize_search()


    def html_main(self):
        return DynamicHTML('resources/search.html', 1).get_html()

    def get_search_progress(self) -> float:
        if self.search_thread:
            if self.search_thread.is_alive():
                total, current = self.memory.get_search_stats()
                if total > 0:
                    return round(100 * current / float(total), 1)
                return 0.0
        return 100.0



    def parse_value(self, size:str, value:str):
        value = value.strip()
        if size == 'array': #special case
            return value
        else:
            ctype = memory_utils.typeToCType[(size, value.strip().startswith("-"))]
            search_value = 1
            if size == 'float':
                search_value = ctype(float(value))
            else:
                search_value = ctype(int(value))
            return search_value

    def reset(self):
        if self.search_thread and self.search_thread.is_alive():
            DataStore().get_operation_control().control_break()
            self.search_thread.join()
        self.stop_updater()
        self.round = 0
        self.search_results.clear()
        self.type = ""
        self.size = ""
        self.value = ""
        self.search_thread: Thread = None
        self.update_thread: Search.UpdateThread = None
        self.previous_stats = {'results': [], 'flow': self.FLOW_START, 'round': 0}
        self.error = ""
        self.progress = Progress()
        self.flow = self.FLOW_START



    def handle_initialization(self, req: Request, resp: Response):
        if self.flow == self.FLOW_START:
            if self.type:
                resp.media['type'] = self.type
            if self.size:
                resp.media['size'] = self.size
            if self.value:
                resp.media['value'] = self.value
        elif self.flow == self.FLOW_SEARCHING:
            resp.media['progress'] = self.progress.get_progress() if self.progress else 0
            resp.media['repeat'] = 1000
            resp.media['round'] = self.round
            resp.media['results'] = []
            resp.media['count'] = 0
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = self.value
        elif self.flow == self.FLOW_RESULTS:
            resp.media['round'] = self.round
            resp.media['results'] = self.get_updated_addresses()
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = self.value
            resp.media['count'] = len(self.search_results)
            resp.media['repeat'] = 0


    def handle_reset(self, req: Request, resp: Response):
        if self.flow == self.FLOW_SEARCHING: #we are stopping
            DataStore().get_operation_control().control_break()
            self.search_thread.join()
            self.search_results = self.previous_stats['results'].copy()
            self.round = self.previous_stats['round']
            self.flow = self.previous_stats['flow']
            resp.media['results'] = self.get_updated_addresses()
            resp.media['round'] = self.round
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = self.value
            resp.media['count'] = len(self.search_results)
        else:
            if self.type in ['increase', 'decrease', 'unchanged', 'changed', 'changed_by']:
                self.type = 'equal_to'
            self.stop_updater()
            self.flow = self.FLOW_START
            resp.media['results'] = []
            self.round = 0
            self.value = ""
            self.size = 'byte_4'
            resp.media['round'] = self.round
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = self.value
            resp.media['count'] = 0
            self.reset()

    def handle_search(self, req: Request, resp: Response):
        if self.search_thread and self.search_thread.is_alive():
            self.memory.break_search()
            self.search_thread.join()
        self.stop_updater()
        self.error = ""
        self.type = req.media['type']
        self.size = req.media['size']
        self.value = req.media['value']
        resp.media['type'] = self.type
        resp.media['size'] = self.size
        resp.media['value'] = self.value
        if req.media['type'] not in self.search_map:
            if self.round == 0:
                self.flow = self.FLOW_START
            raise SearchException("Search type {} is not valid".format(req.media['type']))
        searcher = self.search_map[req.media['type']]
        self.search_thread = Thread(target=self._search, args=[searcher])
        self.previous_stats['flow'] = self.flow
        self.previous_stats['round'] = self.round
        self.previous_stats['results'] = self.search_results.copy()
        self.flow = self.FLOW_SEARCHING
        resp.media['progress'] = 0
        resp.media['repeat'] = 1000
        resp.media['round'] = 0
        resp.media['results'] = []
        resp.media['count'] = 0
        self.search_thread.start()

    def handle_write(self, req: Request, resp: Response):
        if not self.update_thread or not self.update_thread.is_alive():
            raise SearchException("Update thread not running. Can't write value.")
        try:
            addr = int(req.media['address'])
            if self.size == 'array':
                val = memory_utils.value_to_bytes(req.media['value'], memory_utils.aob_size(self.value.strip(), wildcard=True))
            else:
                val = self.parse_value(self.size, str(req.media['value']))
        except Exception:
            raise SearchException("Address or value is not valid for write.")
        finally:
            resp.media['round'] = self.round
            resp.media['results'] = self.get_updated_addresses()
            resp.media['count'] = len(self.search_results)
            resp.media['type'] = self.type
            resp.media['size'] = self.size
            resp.media['value'] = self.value

        self.update_thread.write(addr, val)

    def handle_freeze(self, req: Request, resp: Response):
        if not self.update_thread or not self.update_thread.is_alive():
            raise SearchException("Update thread not running. Can't freeze value.")
        try:
            addr = int(req.media['address'])
            tp = memory_utils.typeToCType[(self.size, False)]
            if self.size == 'array':
                tp = (tp * memory_utils.aob_size(self.value.strip(), wildcard=True))
            val = self.memory.handle.read_memory(addr, tp())
            freeze = req.media['freeze'] == 'true'
        except Exception:
            traceback.print_exc()
            raise SearchException("Address or value is not valid for write.")
        self.update_thread.freeze(addr, val, freeze)

    def handle_result_update(self, req: Request, resp: Response):
        resp.media['results'] = self.get_updated_addresses()
        resp.media['count'] = len(self.search_results)

    def get_updated_addresses(self):
        if not self.update_thread:
            return self.search_results
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
            if self.type in ['equal_to', 'greater_than', 'less_than', 'changed_by']:
                search_value = self.parse_value(self.size, self.value)
            else:
                search_value = 0
        except Exception:
            self.error = 'Could not parse value!'
            return
        self.progress.reset()
        try:
            searcher(search_value)
        except BreakException:
            return
        self._search_complete()

    def _search_complete(self):
        self.round += 1
        if len(self.search_results) > 0:
            self.start_updater()
            self.flow = self.FLOW_RESULTS
        elif self.type == 'unknown':
            self.flow = self.FLOW_INITIALIZE_UNKNOWN
        else:
            self.flow = self.FLOW_NO_RESULTS

    def _equal_search(self, value):
        su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
        if not self.search_results:
            if self.size == 'array':
                addrs = su.search_aob_all_memory(value)
            else:
                addrs = su.search_all_memory(value)
        else:
            if self.size == 'array':
                def cmp(*args):
                    read = args[0]
                    user_input = args[2]
                    for i in range(0, len(user_input)):
                        bt = user_input[i]
                        if bt > 255:
                            continue
                        if bt != read[i]:
                            return False
                    return True
                addrs = su.search_aob_addresses(value, self.search_results, cmp)
            else:
                def cmp(*args):
                    return bytes(args[0]) == bytes(args[2])
                addrs = su.search_addresses(value, self.search_results, cmp)
        self.search_results = [{'address': x, 'value': r} for x, r in addrs]

    def _value_cmp_search(self, value, cmp):
        su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
        if not self.search_results:
            addrs = su.search_cmp_memory(value, cmp)
        else:
            addrs = su.search_addresses(value, self.search_results, cmp)
        self.search_results = [{'address': x, 'value': r} for x, r in addrs]


    def _greater_search(self, value):
        def cmp(*args):
            return args[0].value > args[2].value
        return self._value_cmp_search(value, cmp)

    def _lesser_search(self, value):
        def cmp(*args):
            return args[0].value < args[2].value
        return self._value_cmp_search(value, cmp)


    def _unknown_search(self, _):
        su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
        su.capture_memory()
        self.search_results = []

    def _inc_dec_search(self, cmp):
        su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
        self.value = "-1"
        v = self.parse_value(self.size, self.value)
        if len(self.search_results) == 0:
            addrs = su.search_cmp_capture(v.__class__, cmp)
        else:
            addrs = su.search_cmp_addresses(v.__class__, cmp, self.search_results)
        self.value = ""
        self.search_results = [{'address': x, 'value': r} for x, r in addrs]

    def _increase_search(self, _):
        def cmp(*args):
            return args[0].value > args[1].value
        self._inc_dec_search(cmp)

    def _decrease_search(self, _):
        def cmp(*args):
            return args[0].value < args[1].value
        self._inc_dec_search(cmp)

    def _changed_search(self, _):
        if self.size == 'array':
            su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
            def cmp(*args):
                read = args[0]
                last = args[1]
                for i in range(0, len(last)):
                    bt = last[i]
                    if bt > 255:
                        continue
                    if bt != read[i]:
                        return True
                return False
            addrs = su.search_aob_cmp(self.search_results, cmp)
            self.search_results = [{'address': x, 'value': r} for x, r in addrs]
        else:
            def cmp(*args):
                return args[0].value != args[1].value
            self._inc_dec_search(cmp)

    def _unchanged_search(self, _):
        if self.size == 'array':
            su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
            def cmp(*args):
                read = args[0]
                last = args[1]
                for i in range(0, len(last)):
                    bt = last[i]
                    if bt > 255:
                        continue
                    if bt != read[i]:
                        return False
                return True
            addrs = su.search_aob_cmp(self.search_results, cmp)
            self.search_results = [{'address': x, 'value': r} for x, r in addrs]
        else:
            def cmp(*args):
                return args[0].value == args[1].value
            self._inc_dec_search(cmp)

    def _changed_by_search(self, value):
        su = SearchUtilities(self.mem(), DataStore().get_operation_control(), self.progress)
        def cmp(*args):
            return args[0].value - args[1].value == args[2].value
        if not self.search_results:
            addrs = su.search_cmp_capture(value.__class__, cmp, value)
        else:
            addrs = su.search_addresses(value, self.search_results, cmp)
        self.search_results = [{'address': x, 'value': r} for x, r in addrs]


    def is_done(self):
        if self.search_thread and self.search_thread.is_alive():
            return False
        return True

    def start_updater(self):
        rv = self.search_results[0]['value']
        #if self.size == 'array':
        #    rv = (rv * memory_utils.aob_size(self.value.strip(), wildcard=True))

        self.update_thread = Search.UpdateThread(self.mem(), self.search_results[0:40], rv)
        self.update_thread.start()

    def stop_updater(self):
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.stop.set()
            self.update_thread.join()
        self.update_thread = None

    class UpdateThread(Thread):
        def __init__(self, mem, addrs, pv):
            super().__init__(target=self.process)
            self.memory = mem
            self.stop = Event()
            self.addresses = copy.deepcopy(addrs)
            self.parsed_value = pv
            self.lock = Lock()
            self.write_list = []
            self.freeze_list = {}
            self.error = ""

        def _loop(self):
            try:
                while not self.stop.is_set():
                    self.lock.acquire()
                    if len(self.write_list) > 0:
                        for item in self.write_list:
                            self.memory.write_memory(item[0], item[1])
                        self.write_list.clear()
                    if len(self.freeze_list) > 0:
                        for addr, value in self.freeze_list.items():
                            self.memory.write_memory(addr, value)
                    for i in range(0, len(self.addresses)):
                        if self.stop.is_set():
                            self.lock.release()
                            return
                        addr = self.addresses[i]
                        buf = copy.copy(self.parsed_value)
                        sr = self.memory.read_memory(addr['address'], buf)
                        if isinstance(sr, ctypes.Array):
                            byte_str = ' '.join(memory_utils.bytes_to_aob(sr))
                            self.addresses[i]['value'] = byte_str
                        else:
                            self.addresses[i]['value'] = sr.value
                    self.lock.release()
                    self.stop.wait(1)
            except Exception as e:
                self.error = str(e)
            finally:
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
            if not freeze and address in self.freeze_list:
                del self.freeze_list[address]
            elif freeze and address not in self.freeze_list:
                self.freeze_list[address] = value
            self.lock.release()


