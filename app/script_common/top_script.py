import ctypes
from typing import Union

import mem_edit

from .base_script import BaseScript
from .sub_script import SubScript

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class TopScript(BaseScript):

    def __init__(self):
        super().__init__()
        self.subscripts: dict[str, SubScript] = {}

    def add_script(self, script:SubScript):
        self.subscripts[script.get_id()] = script
        script.user_data = self.user_data
        script.ui = self.ui

    def perform_load(self):
        super().perform_load()
        [script.on_load() for script in self.subscripts.values()]

    def perform_unload(self):
        [script.on_unload() for script in self.subscripts.values()]
        super().perform_unload()

    def get_script(self, _id: str) -> SubScript:
        return self.subscripts.get(_id, None)

    def set_directory(self, directory):
        super().set_directory(directory)
        [script.set_directory(directory) for script in self.subscripts.values()]

    def on_process_attached(self):
        super().on_process_attached()
        [script.on_process_attached() for script in self.subscripts.values()]

    def set_memory(self, mem: mem_edit.Process):
        super().set_memory(mem)
        [script.set_memory(mem) for script in self.subscripts.values()]

    def process(self):
        self.frame()
        [script.frame() for script in self.subscripts.values()]
        self.ui.perform_process()

    def frame(self):
        pass

    def perform_clipboard_copy(self, data):
        super().perform_clipboard_copy(data)
        [script.on_clipboard_copy(data) for script in self.subscripts.values()]

    def perform_clipboard_clear(self):
        super().perform_clipboard_clear()
        [script.on_clipboard_clear() for script in self.subscripts.values()]

    def ready(self):
        self.ui.generate_data_map(self.user_data)
        self.ui.ready()
        [script.on_ready() for script in self.subscripts.values()]
        self.on_ready()
