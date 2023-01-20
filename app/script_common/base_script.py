import ctypes
from typing import Union

import mem_edit

from app.script_common.memory import MemoryManager
from app.script_ui.controls import UI

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class BaseScript:

    def __init__(self):
        self.memory: mem_edit.Process = None
        self.memory_manager: MemoryManager = None
        self.ui = UI(**self.get_script_information())
        self.process_name:str = ""
        self.user_data = {}
        self.include_paths = []
        self.directory: str = ''
        self.clipboard: dict = {}
        self.presented = False


    def perform_load(self):
        self.on_load()
    def on_load(self):
        pass

    def on_process_attached(self):
        pass

    def perform_unload(self):
        self.on_unload()
    def on_unload(self):
        pass

    def set_directory(self, directory):
        self.directory = directory

    def get_process(self):
        script_info = self.get_script_information()
        return script_info.get('process', None)

    def set_memory(self, mem: mem_edit.Process):
        self.memory = mem
        self.memory_manager = MemoryManager(self.memory, self.directory)

    def get_memory(self) -> mem_edit.Process:
        return self.memory

    def get_memory_manager(self):
        return self.memory_manager

    def retrieve_ui_updates(self):
        return self.ui.retrieve_updates()

    def perform_ui_build(self):
        self.build_ui()
        self.ui.perform_build(None)

    def get_html(self):
        return self.ui.get_html()

    def build_ui(self):
        pass

    def get_script_information(self):
        return {}

    def get_speed(self):
        return 1

    def handle_interaction(self, _id, data):
        if _id == '__copy':
            self.clipboard = data
            self.perform_clipboard_copy(data)
            return
        if _id =='__copy_clear':
            self.perform_clipboard_clear()
            self.clipboard.clear()
            return
        self.ui.handle_interaction(_id, data)

    def perform_clipboard_copy(self, data):
        self.on_clipboard_copy(data)
    def on_clipboard_copy(self, data):
        pass

    def perform_clipboard_clear(self):
        self.on_clipboard_clear()

    def on_clipboard_clear(self):
        pass

    def process(self):
        self.frame()
        self.ui.perform_process()

    def frame(self):
        pass

    def get_data(self, key: str):
        if key in self.user_data:
            return self.user_data[key]
        return None

    def put_data(self, key: str, data):
        self.user_data[key] = data

    def ready(self):
        self.ui.generate_data_map(self.user_data)
        self.ui.ready()
        self.on_ready()

    def on_ready(self):
        pass

    def process_released(self):
        pass

    def on_reload(self):
        pass

    def perform_reload(self):
        if self.presented:
            self.ui.on_reload()
            self.on_reload()
        else:
            self.presented = True

