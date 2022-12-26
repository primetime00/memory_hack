import ctypes
from typing import Union

import mem_edit

from app.helpers.directory_utils import scripts_memory_directory
from app.helpers.search_results import SearchResults
from app.script_common.aob import AOB
from app.script_common.utilities import ScriptUtilities
from app.script_ui._base import BaseUI
from app.script_ui.list import ListUI
from app.search.searcher_multi import SearcherMulti as Searcher

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class BaseScript:
    def __init__(self):
        self.memory: mem_edit.Process = None
        self.utilities: ScriptUtilities = None
        self.process_name:str = ""
        self.user_data = {}
        self.include_paths = []
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
            self.utilities = ScriptUtilities(Searcher(mem, None, True, scripts_memory_directory, results=SearchResults(name='script_results', db_path=scripts_memory_directory.joinpath('scripts.db'))))
            self.set_include_paths(self.include_paths)
        else:
            self.utilities = None

    def get_memory(self) -> mem_edit.Process:
        return self.memory

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
        item = self.list_ui.get_id(id)
        item.base_handle_interaction(data)

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


