import time
from threading import Lock

from app.helpers.aob_value import AOBValue


class AOB:
    def __init__(self, name, aob_str):
        self.name = name
        self.aob = AOBValue(aob_str)
        self.aob_string = aob_str
        self.bases = []

        self.last_found_bases = []


        self._last_found = -1
        self._last_searched = -1
        self.base_lock = Lock()

    def get_aob_string(self):
        return self.aob.aob_item['aob_string']

    def get_name(self):
        return self.name

    def is_found(self):
        return len(self.bases) > 0

    def get_bases(self):
        return self.bases

    def set_bases(self, base_list):
        self.bases = base_list
        if base_list:
            self.last_found_bases = base_list.copy()
        self._last_found = len(base_list)

    def clear_bases(self):
        self.bases.clear()
        self._last_found = 0

    def get_last_found_bases(self):
        return self.last_found_bases

    def get_last_searched(self):
        return time.time() - self._last_searched

    def set_last_searched(self):
        self._last_searched = time.time()

    def will_warn(self):
        return self._last_found != 0

    def has_wildcards(self):
        return self.aob.has_wildcards()

    def lock(self):
        self.base_lock.acquire()

    def unlock(self):
        self.base_lock.release()



