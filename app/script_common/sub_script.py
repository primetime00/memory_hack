import ctypes
from typing import Union

import mem_edit

from app.script_common.memory import MemoryManager
from app.script_ui.controls import UI
from app.script_ui.controls.element import Element

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class SubScript():

    def __init__(self, **kwargs):
        super().__init__()
        self.memory: mem_edit.Process = None
        self.memory_manager: MemoryManager = None
        self.user_data: dict = {}
        self.ui: UI = None
        self.directory: str = ""
        self._id = kwargs.get('id', self.__class__.__name__+str(id(self)))

    def get_id(self):
        return self._id

    def on_load(self):
        pass

    def on_unload(self):
        pass

    def get_directory_name(self):
        return self.__class__.__name__.lower()

    def set_directory(self, directory):
        self.directory = directory + '/' + self.get_directory_name()

    def get_directory(self):
        return self.directory

    def get_process(self):
        return None

    def set_memory(self, mem: mem_edit.Process):
        self.memory = mem
        self.memory_manager = MemoryManager(self.memory, self.directory)

    def on_process_attached(self):
        pass

    def get_memory(self) -> mem_edit.Process:
        return self.memory

    def get_memory_manager(self):
        return self.memory_manager

    def build_ui(self, root: Element):
        pass

    def get_script_information(self):
        return {}

    def get_speed(self):
        return 1

    def on_clipboard_copy(self, data):
        pass

    def on_clipboard_clear(self):
        pass

    def frame(self):
        pass

    def get_data(self, key: str):
        if key in self.user_data:
            return self.user_data[key]
        return None

    def put_data(self, key: str, data):
        self.user_data[key] = data

    def on_ready(self):
        pass

    def on_start(self):
        pass

    def on_exit(self):
        pass