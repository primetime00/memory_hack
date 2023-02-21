from threading import Thread, Event, Lock
from time import time

from app.script_common.aob import AOB
from app.script_common.memory import MemoryManager


class AOBScanner:
    def __init__(self, memory_manager: MemoryManager):
        self.mm: MemoryManager = memory_manager
        self.aob_map: {str, AOB} = {}
        self.aob_thread: Thread = None
        self.wait_event: Event = Event()
        self.time_map: {str, float} = {}
        self.search_lock = Lock()
        self.searcher = self.mm.get_searcher(name='aob_scan')
        self.searcher.set_search_size('array')
        self.auto_refresh_time = 7

    def set_auto_refresh(self, refresh):
        self.auto_refresh_time = refresh

    def add(self, aob: AOB) -> AOB:
        if aob.get_aob_string().casefold() not in self.aob_map:
            self.aob_map[aob.get_aob_string().casefold()] = aob
            return aob
        else:
            return self.aob_map[aob.get_aob_string().casefold()]

    def get_valid(self, aob_str: str):
        aob: AOB = self.aob_map.get(aob_str.casefold(), None)
        if not aob:
            return []
        with aob.base_lock:
            if not aob.get_bases():
                return []
            aob.set_bases(self.mm.compare_aob(aob))
            return aob.get_bases()

    def get_addresses(self, aob: str):
        return self.get_valid(aob.casefold())

    def start(self):
        self.aob_thread = Thread(target=self.process)
        self.aob_thread.start()

    def stop(self):
        if self.aob_thread and self.aob_thread.is_alive():
            self.searcher.cancel()
            self.wait_event.set()
            self.aob_thread.join()
        self.aob_thread = None

    def process(self):
        while not self.wait_event.is_set():
            current_time = time()
            if self.aob_map:
                for aob in self.aob_map.values():
                    if len(aob.get_bases()) == 0 or (self.auto_refresh_time > 0 and (current_time - self.time_map.get(aob.get_name(), 0) > self.auto_refresh_time)):
                        self.search_lock.acquire()
                        self.searcher.search_memory_value(aob.get_aob_string())
                        results = [x['address'] for x in self.searcher.get_results(limit=100)]
                        self.search_lock.release()
                        if len(results) > 0:
                            aob.lock()
                            aob.set_bases(results)
                            self.time_map[aob.get_name()] = current_time
                            aob.unlock()
            self.wait_event.wait(2.0)



