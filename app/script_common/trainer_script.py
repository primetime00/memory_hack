import ctypes
from typing import Union, cast

import app.script_ui.controls as controls
from app.script_common.aob import AOB
from app.script_common.aob_scanner import AOBScanner
from app.script_common.memory import MemoryManager
from .base_script import BaseScript

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class TrainerScript(BaseScript):

    def __init__(self):
        super().__init__()
        self.aob_codes = {}
        self.address_codes = {}
        self.pointer_codes = {}
        self.name_map = {}
        self.callback_map = {}
        self.aob_scanner: AOBScanner = None
        self.ui_map = {}

    def on_unload(self):
        if self.aob_scanner:
            self.aob_scanner.stop()

    def create_codes(self):
        pass

    def on_process_attached(self):
        self.aob_scanner = AOBScanner(self.memory_manager)
        TrainerScript.Code.mm = self.memory_manager
        TrainerScript.Code.scanner = self.aob_scanner
        self.create_codes()
        if len(self.aob_codes) > 0:
            self.aob_scanner.start()


    def add_aob_code(self, name:str, aob:str, offset: [str]):
        actual_aob = self.aob_scanner.add(AOB(name, aob))
        self.aob_codes[name] = TrainerScript.Code(name, offset=offset, aob=actual_aob)
        self.name_map[name] = self.aob_codes[name]


    def add_address_code(self, name: str, address: str):
        if ':' not in address:
            address = address.casefold()
        if address not in self.address_codes:
            self.address_codes[address] = []
        code = TrainerScript.Code(name, address=address)
        #code = {'name': name, 'address': address}
        self.address_codes[address].append(code)
        self.name_map[name] = code

    def add_pointer_code(self, name: str, address: str, offsets: str):
        if ':' not in address:
            address = address.casefold()
        if address not in self.pointer_codes:
            self.pointer_codes[address] = []
        code = TrainerScript.Code(name, offsets=offsets, pointer=address)
        #code = {'name': name, 'offsets': offsets, 'pointer': address}
        self.pointer_codes[address].append(code)
        self.name_map[name] = code

    def write(self, addr: int, value: ctypes_buffer_t):
        self.memory.write_memory(addr, value)

    def read(self, addr: int, value: ctypes_buffer_t):
        return self.memory.read_memory(addr, value)

    def write_code(self, name: str, value: ctypes_buffer_t):
        code: TrainerScript.Code = self.get_code(name)
        if code:
            return code.write(value)
        return False

    def read_code(self, name: str, value: ctypes_buffer_t):
        code: TrainerScript.Code = self.get_code(name)
        if code:
            return code.read(value)
        return []


    def get_code(self, name: str) -> 'TrainerScript.Code':
        code = self.name_map.get(name, None)
        if not code:
            return None
        return code

    def add_text(self, text: str, row: int, **kwargs):
        ctrl = controls.Text(text, **kwargs)
        self.add_control(ctrl, row)

    def add_space(self, row: int, **kwargs):
        ctrl = controls.Space(**kwargs)
        self.add_control(ctrl, row)

    def add_input(self, _default: str, callback: callable, row: int, **kwargs):
        ctrl = controls.Input(self._callback, text=_default, **kwargs)
        self.callback_map[ctrl.get_id()] = callback
        self.add_control(ctrl, row)

    def _callback(self, name, _id, data):
        cb = self.callback_map[name]
        if cb:
            cb(self.get_control(name))

    def add_button(self, label: str,  callback: callable, row: int, **kwargs):
        quiet = kwargs.get('quiet', False)
        ctrl = controls.Button(label, self._callback, quiet, **kwargs)
        self.callback_map[ctrl.get_id()] = callback
        self.add_control(ctrl, row)

    def add_toggle(self, _default: str, callback: callable, row: int, **kwargs):
        ctrl = controls.Toggle(self._callback, **kwargs)
        if _default.casefold() == 'on':
            ctrl.check()
        self.callback_map[ctrl.get_id()] = callback
        self.add_control(ctrl, row)

    def add_select(self, values: list, selection: str, callback: callable, row: int, **kwargs):
        ctrl = controls.Select(values, self._callback, **kwargs)
        try:
            idx = [v[0] for v in values].index(selection)
            if idx > 0:
                ctrl.set_value(selection)
        except:
            pass
        self.callback_map[ctrl.get_id()] = callback
        self.add_control(ctrl, row)


    def add_control(self, ctrl: controls.Element, row: int):
        if row not in self.ui_map:
            self.ui_map[row] = []
        self.ui_map[row].append(ctrl)

    def get_control(self, _id: str) -> controls.Element:
        return self.ui.get_element(_id)

    def define_ui(self):
        pass

    def build_ui(self):
        self.define_ui()
        main_page = self.ui.add_page(controls.Page(id='MAIN_PAGE'))
        for row in sorted(self.ui_map.keys()):
            elements: [controls.Element] = self.ui_map[row]
            main_page.add_elements(elements)

    def frame(self):
        self.process_codes()

    def process_codes(self):
        pass

    def disable_row(self, row: int):
        elements = self.ui_map.get(row, [])
        for ele in elements:
            cast(controls.Element, ele).disable()

    def enable_row(self, row: int):
        elements = self.ui_map.get(row, [])
        for ele in elements:
            cast(controls.Element, ele).enable()



    class Code:
        mm: MemoryManager = None
        scanner: AOBScanner = None

        def __init__(self, name:str, **kwargs):
            self.name = name
            self.aob: AOB = kwargs.get('aob', None)
            offset = kwargs.get('offset', None)
            if offset:
                self.offset = [int(x, 16) for x in offset]
            else:
                self.offset = [0]
            self.pointer = kwargs.get('pointer', None)
            self.offsets = kwargs.get('offsets', None)
            self.address = kwargs.get('address', None)

        def get_addresses(self):
            if self.aob:
                addrs = self.scanner.get_addresses(self.aob.get_aob_string())
                return sum([[x+y for x in addrs] for y in self.offset], [])
            if self.pointer:
                base = self.mm.read_pointer(self.pointer, self.offsets, return_base=True)
                return [base] if base is not None else []
            if self.address:
                addr = self.mm.get_address(self.address)
                return [addr] if addr is not None else []
            return []

        def write(self, value: ctypes_buffer_t):
            addrs = self.get_addresses()
            if len(addrs) == 0:
                return False
            for addr in addrs:
                self.mm.memory.write_memory(addr, value)
            return True

        def read(self, value: ctypes_buffer_t):
            addrs = self.get_addresses()
            vals = []
            for addr in addrs:
                vals.append(type(value)())
                self.mm.memory.read_memory(addr, vals[-1])
            return vals









