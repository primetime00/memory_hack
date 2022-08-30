import copy
import ctypes
import logging
import time
from threading import Thread, Lock

from app.helpers import MemoryEditor, DynamicHTML, MemoryHandler, DataStore
from app.helpers import memory_utils

class Search(MemoryHandler):
    def __init__(self):
        super().__init__()
        self.type = ""
        self.size = ''
        self.value = ""
        self.search_thread: Thread = None
        self.update_thread: Search.UpdateThread = None
        self.search_addresses = []
        self.iterations = 0
        self.searching = False
        self.error = ""

    def release(self):
        self.reset()

    def html_main(self):
        return DynamicHTML('resources/search.html', 1).get_html()

    def is_running(self):
        return (self.search_thread is not None and self.search_thread.is_alive()) or (self.update_thread is not None and self.update_thread.is_alive())


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
        self.iterations = 0
        self.searching = False
        self.search_addresses.clear()

    def search(self, data, resp):
        if 'initialize' in data:
            resp.status = 200

            if len(self.error) > 0:
                status = "ERROR"
            elif self.iterations == 0:
                status = "WAITING_START"
            elif self.iterations > 0:
                status = "WAITING_CONTINUE"
            else:
                status = "WAITING_CONTINUE"
            if self.search_thread and self.search_thread.is_alive():
                status = "SEARCHING"

            if self.update_thread and self.update_thread.is_alive():
                addrs = self.update_thread.get_addresses()
            else:
                addrs = []

            resp.media = self.get_response(status, True, addrs)
            return
        if 'reset' in data:
            self.reset()
            resp.status = 200
            resp.media = self.get_response('WAITING_START', False, [])
            return
        if 'write' in data:
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.write(int(data['write']), data['value'])
        if 'button' not in data:
            resp.status = 400
            resp.media = self.get_response('INCORRECT_FORM', True, [])
            return
        if 'update_address' in data:
            if self.update_thread and self.update_thread.is_alive():
                addrs = self.update_thread.get_addresses()
            else:
                logging.warning('Could not get addresses because thread is no longer active.')
                addrs = []
            resp.status = 200
            resp.media = self.get_response('UPDATE_ADDRESSES', True, self.convert_addresses(addrs), length=len(addrs))
            return
        if data['button'] == 'false':
            if not self.searching:
                if len(self.error) > 0:
                    resp.media = self.get_response('ERROR', False, [])
                elif self.iterations == 0:
                    resp.media = self.get_response('WAITING_START', False, [])
                else:
                    resp.media = self.get_response('WAITING_CONTINUE', True, self.convert_addresses(self.search_addresses), length=len(self.search_addresses))
            else:
                resp.media = self.get_response('SEARCHING', False, self.convert_addresses(self.search_addresses), length=len(self.search_addresses), progress=self.get_search_progress())
            resp.status = 200
        else:
            if self.iterations == 0:
                self.type = data['type']
                self.size = data['size']
                self.process = data['process']
            self.value = data['value']
            target = self._exact_search if self.type == 'exact' else self._unknown_search
            self.search_thread = Thread(target=target)
            self.searching = True
            resp.media = self.get_response('SEARCHING', False, [])
            self.search_thread.start()
            resp.status = 200

    @staticmethod
    def convert_addresses(addrs):
        if len(addrs) == 0:
            return []
        return [('0x{0:0{1}X}'.format(x[0], 16), x[1]) for x in addrs[0:40]]

    def _exact_search(self):
        self.error = ""
        self.stop_updater()
        try:
            search_value = self.parse_value(self.size, self.value)
        except Exception:
            self.error = 'Could not parse value!'
            self.searching = False
            return
        if self.iterations == 0:
            addrs = self.memory.search_exact(search_value) if not isinstance(search_value, str) else self.memory.search_aob(search_value)
        else:
            old_addrs = [x[0] for x in self.search_addresses]
            addrs = self.memory.search_exact(search_value, addresses=old_addrs) if not isinstance(search_value, str) else self.memory.search_aob(search_value, addresses=old_addrs)
        self.search_addresses = [(x, self.value) for x in addrs]
        tp = memory_utils.typeToCType[(self.size, self.value.strip().startswith("-"))]
        if self.size == 'array':
            tp = (tp * memory_utils.aob_size(self.value.strip()))
        self.update_thread = Search.UpdateThread(self.search_addresses[0:40], self.process, tp, self.size, self.memory)
        self.update_thread.start()
        self.iterations += 1
        self.searching = False

    def _unknown_search(self):
        self.error = ""
        self.stop_updater()
        addrs = []
        if self.iterations == 0:
            self.memory.store_memory()
        elif self.iterations == 1:
            addrs = self.memory.compare_store(self.value, self.size)
            self.search_addresses = [(x['address'], x['current'], x['first']) for x in addrs]
        elif self.search_addresses:
            addrs = self.memory.compare_store(self.value, self.size, previous_addresses=self.search_addresses)
            self.search_addresses = [(x['address'], x['current'], x['first']) for x in addrs]
        if len(addrs) > 0:
            self.update_thread = Search.UpdateThread(self.search_addresses[0:40], self.process, memory_utils.typeToCType[(self.size, False)], self.size, self.memory)
            self.update_thread.start()
        self.iterations += 1
        self.searching = False

    def is_done(self):
        if self.search_thread and self.search_thread.is_alive():
            return False
        return True

    def stop_updater(self):
        if self.update_thread and self.update_thread.is_alive():
            self.update_thread.stop = True
            self.update_thread.join()
        self.update_thread = None

    def get_response(self, status, complete, addrs, length=0, progress=0.0):
        return  {'status': status,
                'process': DataStore().get_process(),
                'type': self.type,
                'size': self.size,
                'value': self.value,
                'complete': complete,
                'count': len(addrs) if length == 0 else length,
                'addresses': addrs,
                'progress': progress,
                'error': self.error,
                'iteration': self.iterations}

    class UpdateThread(Thread):
        def __init__(self, addrs, process, type, size, memory):
            super().__init__(target=self.process)
            self.memory = memory
            self.stop = False
            self.addresses = copy.deepcopy(addrs)
            self.proc = process
            self.type = type
            self.size = MemoryEditor.size_map[size]
            self.lock = Lock()
            self.write_list = []

        def process(self):
            while not self.stop:
                self.lock.acquire()
                if len(self.write_list) > 0:
                    for item in self.write_list:
                        self.memory.handle.write_memory(item[0], memory_utils.value_to_bytes(item[1], self.size))
                    self.write_list.clear()
                for i in range(0, len(self.addresses)):
                    if self.stop:
                        self.lock.release()
                        return
                    addr = self.addresses[i]
                    sr = self.memory.read(addr[0], self.type())
                    if isinstance(sr, ctypes.Array):
                        byte_str = ' '.join(memory_utils.bytes_to_aob(sr))
                        self.addresses[i] = (addr[0], byte_str)
                    else:
                        self.addresses[i] = (addr[0], sr.value)
                self.lock.release()
                if self.stop:
                    break
                time.sleep(1)

        def get_addresses(self):
            res = []
            self.lock.acquire()
            res = copy.deepcopy(self.addresses)
            self.lock.release()
            return res

        def write(self, address, value):
            self.lock.acquire()
            self.write_list.append((address, value))
            self.lock.release()


