import copy
import ctypes
import logging
import time
import traceback
from threading import Thread, Lock
from falcon import Request, Response
from falcon.app_helpers import MEDIA_JSON
from app.helpers.exceptions import SearchException

from app.helpers import MemoryEditor, DynamicHTML, MemoryHandler, DataStore
from app.helpers import memory_utils

class Search(MemoryHandler):
    def __init__(self):
        super().__init__()
        self.handle_map = {
            "SEARCH_INITIALIZE": self.handle_initialization,
            "SEARCH_RESET": self.handle_reset,
            "SEARCH_START": self.handle_search,
            "SEARCH_STATUS": self.handle_initialization,
            "SEARCH_WRITE": self.handle_write,
            "SEARCH_FREEZE": self.handle_freeze
        }
        self.type = ""
        self.last_search = ""
        self.size = ""
        self.value = ""
        self.direction = ""
        self.search_thread: Thread = None
        self.update_thread: Search.UpdateThread = None
        self.search_addresses = []
        self.round = 0
        self.error = ""

    def release(self):
        self.reset()

    def set(self, handler, process):
        self.memory.initialize_search()

    def html_main(self):
        return DynamicHTML('resources/search.html', 1).get_html()

    def is_running(self):
        return (self.search_thread is not None and self.search_thread.is_alive()) or (self.update_thread is not None and self.update_thread.is_alive())

    def is_searching(self):
        return self.search_thread is not None and self.search_thread.is_alive()

    def has_searched(self):
        if not self.last_search:
            return False
        return not self.is_searching()

    def is_updating(self):
        return self.update_thread is not None and self.update_thread.is_alive()

    def is_ready_for_start(self):
        if self.update_thread and self.update_thread.is_alive():
            return False
        if self.search_thread and self.search_thread.is_alive():
            return False
        if self.last_search == "":
            return True

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
            return value.strip()
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
            self.memory.break_search()
            self.search_thread.join()
        self.stop_updater()
        if self.memory:
            self.memory.initialize_search()
        self.round = 0
        self.last_search = ""
        self.search_addresses.clear()

    def handle_initialization(self, req: Request, resp: Response):
        #We just loaded the page. Check if search is idle, running, or finished
        state = 'SEARCH_STATE_UNKNOWN'
        if self.is_ready_for_start():
            resp.media['state'] = 'SEARCH_STATE_START'
            resp.media['repeat'] = 0
            resp.media['search_type'] = "exact"
        elif self.is_searching():
            resp.media['state'] = 'SEARCH_STATE_SEARCHING'
            resp.media['repeat'] = 1000
            resp.media['progress'] = self.get_search_progress()
        elif self.has_searched():
            resp.media['state'] = 'SEARCH_STATE_CONTINUE'
            resp.media['search_type'] = self.type
            resp.media['number_of_results'] = len(self.search_addresses)
            resp.media['search_results'] = self.get_updated_addresses() if self.last_search != 'UNKNOWN_INITIAL' else []
            resp.media['last_search'] = self.last_search
            resp.media['search_round'] = self.round
            resp.media['repeat'] = 1000 if self.search_addresses else 0


    def handle_reset(self, req: Request, resp: Response):
        self.reset()

        resp.media['state'] = "SEARCH_STATE_START"
        resp.media['progress'] = 0
        resp.media['search_type'] = "exact"
        resp.media['search_round'] = 0
        resp.media['number_of_results'] = 0
        resp.media['search_results'] = []

    def handle_search(self, req: Request, resp: Response):
        if self.search_thread and self.search_thread.is_alive():
            self.memory.break_search()
            self.search_thread.join()
        self.stop_updater()
        self.error = ""
        searcher = self._exact_search if req.media['type'] == 'exact' else self._unknown_search
        self.size = req.media['size']
        self.value = req.media['value']
        self.direction = req.media['direction']
        self.type = req.media['type']
        self.search_thread = Thread(target=searcher)
        self.search_thread.start()

        resp.media['state'] = "SEARCH_STATE_SEARCHING"
        resp.media['progress'] = 0
        resp.media['repeat'] = 1000
        resp.media['search_type'] = self.type
        resp.media['search_round'] = 0
        resp.media['number_of_results'] = 0
        resp.media['search_results'] = []

    def handle_write(self, req: Request, resp: Response):
        if not self.update_thread or not self.update_thread.is_alive():
            raise SearchException("Update thread not running. Can't write value.")
        try:
            addr = int(req.media['address'])
            if self.size == 'array':
                val = memory_utils.value_to_bytes(req.media['value'], memory_utils.aob_size(self.value.strip(), wildcard=True))
            else:
                val = memory_utils.value_to_bytes(req.media['value'], MemoryEditor.size_map[self.size])
        except Exception:
            raise SearchException("Address or value is not valid for write.")
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

    def get_updated_addresses(self):
        if not self.update_thread:
            return []
        if self.last_search != 'UNKNOWN_INITIAL':
            return self.update_thread.get_addresses()
        return []


    def process(self, req: Request, resp: Response):
        resp.media = {}
        command = req.media['command']
        assert (command in self.handle_map)
        resp.content_type = MEDIA_JSON
        try:
            self.handle_map[command](req, resp)
        except SearchException as e:
            resp.media['error'] = e.get_message()


    def _search_complete(self):
        self.round += 1
        if len(self.search_addresses) > 0:
            self.start_updater()

    def _exact_search(self):
        self.stop_updater()
        try:
            search_value = self.parse_value(self.size, self.value)
        except Exception:
            self.error = 'Could not parse value!'
            return
        if not self.search_addresses:
            addrs = self.memory.search_exact(search_value) if not isinstance(search_value, str) else self.memory.search_aob(search_value)
            self.last_search = "EXACT_INITIAL"
        else:
            old_addrs = [x['address'] for x in self.search_addresses]
            addrs = self.memory.search_exact(search_value, addresses=old_addrs) if not isinstance(search_value, str) else self.memory.search_aob(search_value, addresses=old_addrs)
            self.last_search = "EXACT_CONTINUE"
        self.search_addresses = [{'address': x, 'value': self.value} for x in addrs]
        self._search_complete()

    def _unknown_search(self):
        self.stop_updater()
        if not self.memory.has_memory_files():
            self.memory.store_memory()
            self.last_search = "UNKNOWN_INITIAL"
        elif not self.search_addresses:
            self.search_addresses = self.memory.compare_store(self.direction, self.size)
            self.last_search = "UNKNOWN_COMPARE_INITIAL"
        else:
            self.search_addresses = self.memory.compare_store(self.direction, self.size, previous_addresses=self.search_addresses)
            self.last_search = "UNKNOWN_COMPARE"

        self._search_complete()

    def is_done(self):
        if self.search_thread and self.search_thread.is_alive():
            return False
        return True

    def start_updater(self):
        tp = memory_utils.typeToCType[(self.size, self.value.strip().startswith("-"))]
        if self.size == 'array':
            tp = (tp * memory_utils.aob_size(self.value.strip(), wildcard=True))

        self.update_thread = Search.UpdateThread(self.search_addresses[0:40], tp, self.size, self.memory)
        self.update_thread.start()

    def stop_updater(self):
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.stop = True
            self.update_thread.join()
        self.update_thread = None

    class UpdateThread(Thread):
        def __init__(self, addrs, type, size, memory):
            super().__init__(target=self.process)
            self.memory = memory
            self.stop = False
            self.addresses = copy.deepcopy(addrs)
            self.type = type
            if size == 'array':
                self.size = type._length_
            else:
                self.size = MemoryEditor.size_map[size]
            self.lock = Lock()
            self.write_list = []
            self.freeze_list = {}
            self.error = ""

        def _loop(self):
            while not self.stop:
                self.lock.acquire()
                if len(self.write_list) > 0:
                    for item in self.write_list:
                        self.memory.handle.write_memory(item[0], item[1])
                    self.write_list.clear()
                if len(self.freeze_list) > 0:
                    for addr, value in self.freeze_list.items():
                        self.memory.handle.write_memory(addr, value)
                for i in range(0, len(self.addresses)):
                    if self.stop:
                        self.lock.release()
                        return
                    addr = self.addresses[i]
                    sr = self.memory.read(addr['address'], self.type())
                    if isinstance(sr, ctypes.Array):
                        byte_str = ' '.join(memory_utils.bytes_to_aob(sr))
                        self.addresses[i]['value'] = byte_str
                    else:
                        self.addresses[i]['value'] = sr.value
                self.lock.release()
                if self.stop:
                    break
                time.sleep(1)

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


