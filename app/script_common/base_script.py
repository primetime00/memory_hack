import ctypes
import re
from typing import Union

import mem_edit

from app.helpers.process import get_process_map
from app.script_common.aob import AOB
from app.script_common.utilities import ScriptUtilities
from app.script_ui._base import BaseUI
from app.script_ui.list import ListUI

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class BaseScript:

    re_fn = r'^((?!(?:COM[0-9]|CON|LPT[0-9]|NUL|PRN|AUX|com[0-9]|con|lpt[0-9]|nul|prn|aux)|\s|[\.]{2,})[^\\\/:*"?<>|]{1,254}(?<![\s\.])):(\d+)\+([0-9a-f]+)$'
    re_addr = '^[0-9A-F]{5,16}$'
    re_of = r'^\d+(, ?\d+)*$'

    def __init__(self):
        self.memory: mem_edit.Process = None
        self.utilities: ScriptUtilities = None
        self.process_name:str = ""
        self.user_data = {}
        self.include_paths = []
        self.path_cache = {}
        self.list_ui: ListUI = ListUI()
        self.build_ui()

    aobs = set()

    def on_load(self):
        self.aobs.clear()
        pass

    def on_unload(self):
        if self.utilities and self.utilities.searcher:
            self.utilities.searcher.cancel()
        self.aobs.clear()

    def set_memory(self, mem: mem_edit.Process):
        self.memory = mem
        if mem:
            self.utilities = ScriptUtilities(mem, 'script')
            self.set_include_paths(self.include_paths)
        else:
            self.utilities = None

    def get_memory(self) -> mem_edit.Process:
        return self.memory

    def get_address(self, addr: str):
        if addr in self.path_cache:
            return self.path_cache[addr]
        pm = self.get_data("_PROCESS_MAP")
        if pm is None:
            pm = get_process_map(self.memory, include_paths=self.include_paths)
            self.put_data("_PROCESS_MAP", pm)
        if ':' in addr:
            for process in pm:
                matcher = re.match(self.re_fn, addr.strip(), re.IGNORECASE)
                if process['pathname'].endswith(matcher.group(1)) and process['map_index'] == int(matcher.group(2)):
                    res = process['start'] + int(matcher.group(3), 16)
                    self.path_cache[addr] = res
                    return res
            return None
        else:
            return int(addr, 16)

    def process_pointer(self, address: str, offsets: str, return_base: bool = False):
        addr = self.get_address(address)
        offset_values = [int(x.strip(), 16) for x in offsets.split(',')]
        try:
            offset = 0
            for offset in offset_values:
                read = self.get_memory().read_memory(addr, ctypes.c_uint64()).value
                read = read + offset
                addr = read
            return addr - offset if return_base else addr
        except Exception:
            return None

    def offsets_to_string(self, offsets: list):
        return ", ".join("{:X}".format(x) for x in offsets)

    def string_to_offsets(self, offsets: str):
        return [int(x.strip(), 16) for x in offsets.split(",")]


    def set_process(self, proc: str):
        self.process_name = proc

    def get_process(self) -> str:
        return self.process_name

    def add_ui_element(self, element: BaseUI):
        self.list_ui.add(element)

    def get_ui_control(self, name: str):
        return self.list_ui.get_by_name(name)

    def get_ui(self):
        ui = "<h2>{}</h2>".format(self.get_name())
        ui += "<h3>{}</h3>".format(self.get_process())
        return ui+self.list_ui.present()

    def build_ui_status(self, item: BaseUI, data):
        if item.children:
            for c in item.children:
                self.build_ui_status(c, data)
        if not item.update_queue.empty():
            data[item.get_id()] = []
        while not item.update_queue.empty():
            data[item.get_id()].append(item.update_queue.get())

    def get_ui_status(self):
        update_status = {}
        for item in self.list_ui.ui_list:
            self.build_ui_status(item, update_status)
        return update_status

    def build_ui(self):
        pass

    def process_lost(self):
        self.aobs.clear()

    def add_aob(self, aob: AOB):
        self.aobs.add(aob)

    def get_app(self):
        return []

    def get_name(self):
        return 'default'

    def get_speed(self):
        return 1

    def handle_interaction(self, id, data):
        if id == '__copy':
            self.on_clipboard_copy(data)
            return
        if id =='__copy_clear':
            self.on_clipboard_clear()
            return
        item = self.list_ui.get_id(id)
        item.base_handle_interaction(data)

    def on_clipboard_copy(self, data):
        pass

    def on_clipboard_clear(self):
        pass


    def _on_aob_lost(self, aob: AOB):
        self.on_aob_lost(aob)
        #for item in self.list_ui.ui_list:
        #    item.update_status()

    def on_aob_lost(self, aob: AOB):
        pass

    def _on_aob_found(self, aob: AOB):
        self.on_aob_found(aob)
        #for item in self.list_ui.ui_list:
        #    item.update_status()

    def on_aob_found(self, aob: AOB):
        pass


    def _search(self):
        for aob in self.aobs:
            addresses = self.utilities.search_aob(aob)
            prev_bases = aob.get_bases()
            new_addresses = set(addresses) - set(prev_bases)
            same_addresses = set(prev_bases) & set(addresses)
            new_bases = list(new_addresses) + list(same_addresses)
            if len(new_bases) == 0 and len(prev_bases) > 0:
                self._on_aob_lost(aob)
            aob.lock()
            aob.set_bases(new_bases)
            aob.unlock()
            if len(new_addresses) > 0:
                self._on_aob_found(aob)


    def check_aobs(self):
        for aob in self.aobs:
            aob.lock()
            prev_bases = aob.get_bases()
            bases = self.utilities.compare_aob(aob)
            if len(prev_bases) > 0 and len(bases) == 0:
                self._on_aob_lost(aob)
            aob.set_bases(bases)
            aob.unlock()

    def process(self):
        self.frame()
        for item in self.list_ui.ui_list:
            item.base_process()

    def frame(self):
        pass

    def get_data(self, key: str):
        if key in self.user_data:
            return self.user_data[key]
        return None

    def put_data(self, key: str, data):
        self.user_data[key] = data

    def write_pointer(self, address: int, offsets: list, value: ctypes_buffer_t, error_func: callable = None):
        try:
            for offset in offsets:
                v = self.memory.read_memory(address, ctypes.c_uint64()).value
                v = v + offset
                address = v
            self.memory.write_memory(address, value)
        except Exception as e:
            if error_func:
                error_func(e)

    def read_pointer(self, address: int, offsets: list, error_func: callable = None):
        try:
            for offset in offsets:
                v = self.memory.read_memory(address, ctypes.c_uint64()).value
                v = v + offset
                address = v
            return address
        except Exception as e:
            if error_func:
                error_func(e)
        return None

    def set_include_paths(self, paths: list):
        self.include_paths = paths
        if self.utilities and self.utilities.searcher:
            self.utilities.searcher.set_include_paths(self.include_paths)


