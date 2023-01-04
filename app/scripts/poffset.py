import platform
import re

from app.helpers.data_store import DataStore
from app.helpers.process import get_process_map
from app.script_common import BaseScript
from app.script_ui import BaseUI, Button, Select, Input, Text


class PointerOffset(BaseScript):
    re_fn = r'^((?!(?:COM[0-9]|CON|LPT[0-9]|NUL|PRN|AUX|com[0-9]|con|lpt[0-9]|nul|prn|aux)|\s|[\.]{2,})[^\\\/:*"?<>|]{1,254}(?<![\s\.])):(\d+)\+([0-9a-f]+)$'
    re_addr = '^[0-9A-F]{5,16}$'
    re_of = r'^\d+(, ?\d+)*$'

    def on_load(self):
        self.put_data("SYSTEM", platform.system())
        self.put_data("INPUT_CHANGE", False)

    def get_name(self):
        return "Pointer Offseter"

    def get_app(self):
        return []

    def build_ui(self):
        self.add_ui_element(Select("PROCS", "Process", values=[('none', "None")], on_changed=self.ctrl_changed, children=[Button("REFRESH", "Refresh", on_pressed=self.refresh_pid)]))
        self.add_ui_element(Input("POINTER_ADDRESS", "Pointer Address", on_changed=self.ctrl_changed, change_on_focus=False, children=[Button("PASTE_POINTER", "Paste", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Input("POINTER_OFFSETS", "Pointer Offsets", on_changed=self.ctrl_changed, change_on_focus=False))
        self.add_ui_element(Input("OUTPUT_ADDRESS", "Output Address", on_changed=self.ctrl_changed, change_on_focus=False, children=[Button("PASTE_ADDRESS", "Paste", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Text("RESULT_ADDRESS", "Result Pointer", children=[Button("COPY_ADDRESS", "Copy", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Text("RESULT_OFFSETS", "Result Offsets"))

        self.refresh_pid(self.get_ui_control("PROCS"))

        [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['POINTER_ADDRESS', 'POINTER_OFFSETS', 'PASTE_POINTER', 'OUTPUT_ADDRESS', 'PASTE_ADDRESS', 'RESULT_ADDRESS', 'COPY_ADDRESS', 'RESULT_OFFSETS']]


    def refresh_pid(self, ele: BaseUI):
        procs = [(x,x) for x in DataStore().get_service('process').get_process_list()]
        procs.insert(0, ('_null', ''))
        self.get_ui_control("PROCS").set_values(procs)

    def on_clipboard_copy(self, data):
        show_paste_pointer = False
        show_paste_address = False
        if 'address' in data and 'offsets' in data:
            self.put_data("CLIPBOARD_POINTER", data)
            show_paste_pointer = True
            if 'resolved' in data:
                self.put_data("CLIPBOARD_ADDRESS", {'address': data['resolved']})
                show_paste_address = True
        elif 'address' in data:
            self.put_data("CLIPBOARD_ADDRESS", {'address': data['address']})
            show_paste_address = True
        self.get_ui_control("PASTE_POINTER").show() if show_paste_pointer else self.get_ui_control("PASTE_POINTER").hide()
        self.get_ui_control("PASTE_ADDRESS").show() if show_paste_address else self.get_ui_control("PASTE_ADDRESS").hide()


    def on_clipboard_clear(self):
        self.get_ui_control("PASTE_POINTER").hide()
        self.get_ui_control("PASTE_ADDRESS").hide()

    def ctrl_changed(self, ele: BaseUI, value):
        if ele.get_name() == 'POINTER_ADDRESS' or ele.get_name() == 'POINTER_OFFSETS' or ele.get_name() == 'OUTPUT_ADDRESS':
            self.put_data("INPUT_CHANGE", True)
        elif ele.get_name() == 'PROCS':
            DataStore().get_service('script').set_app(self.get_ui_control("PROCS").get_selection())
            self.put_data('APP_NAME', self.get_ui_control("PROCS").get_selection())
            if value != '_null':
                [self.get_ui_control(ctrl_name).show() for ctrl_name in ['POINTER_ADDRESS', 'POINTER_OFFSETS', 'OUTPUT_ADDRESS']]
                self.put_data("PROCESS_MAP", get_process_map(self.get_memory()))
            else:
                [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['POINTER_ADDRESS', 'POINTER_OFFSETS', 'PASTE_POINTER', 'OUTPUT_ADDRESS', 'PASTE_ADDRESS', 'RESULT_ADDRESS', 'COPY_ADDRESS', 'RESULT_OFFSETS']]

    def check_for_calculate(self):
        if all(len(self.get_ui_control(x).get_text()) > 0 for x in ['POINTER_ADDRESS', 'POINTER_OFFSETS', 'OUTPUT_ADDRESS']):
            if self.address_validator(self.get_ui_control('POINTER_ADDRESS').get_text()) and self.address_validator(self.get_ui_control('OUTPUT_ADDRESS').get_text()) and self.offsets_validator(self.get_ui_control('POINTER_OFFSETS').get_text()):
                pt = self.calculate_pointer()
                if pt is None:
                    [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['RESULT_ADDRESS', 'COPY_ADDRESS', 'RESULT_OFFSETS']]
                    self.get_ui_control("RESULT_OFFSETS").set_text("Invalid pointer calculated.")
                    self.get_ui_control("RESULT_OFFSETS").show()
                else:
                    self.get_ui_control("RESULT_ADDRESS").set_text(pt['pointer'])
                    self.get_ui_control("RESULT_OFFSETS").set_text(pt['offsets'])
                    [self.get_ui_control(ctrl_name).show() for ctrl_name in ['RESULT_ADDRESS', 'COPY_ADDRESS', 'RESULT_OFFSETS']]
                self.put_data("RESULT_POINTER", pt)

    def ctrl_pressed(self, ele: BaseUI):
        if ele.get_name() == 'PASTE_POINTER':
            self.get_ui_control("POINTER_ADDRESS").set_text(self.get_data("CLIPBOARD_POINTER")['address'])
            self.get_ui_control("POINTER_OFFSETS").set_text(self.get_data("CLIPBOARD_POINTER")['offsets'])
            self.check_for_calculate()
        elif ele.get_name() == 'PASTE_ADDRESS':
            self.get_ui_control("OUTPUT_ADDRESS").set_text(self.get_data("CLIPBOARD_ADDRESS")['address'])
            self.check_for_calculate()
        elif ele.get_name() == 'COPY_ADDRESS':
            rp = self.get_data("RESULT_POINTER")
            ele.update_queue.put({'op': "script", 'data': {'script': 'document.clipboard.copy({{"address": "{}", "offsets": "{}"}})'.format(rp['pointer'], rp['offsets'])}})

    def address_validator(self, txt: str):
        if re.match(self.re_fn, txt.upper().strip()) or re.match(self.re_addr, txt.upper().strip()):
            return True
        return False

    def offsets_validator(self, txt: str):
        if re.match(self.re_of, txt.upper().strip()):
            return True
        return False


    def frame(self):
        if self.get_data("INPUT_CHANGE"):
            self.check_for_calculate()

    def is_linux(self):
        return self.get_data("SYSTEM") == 'Linux'

    def calculate_pointer(self):
        pointer_address = self.get_ui_control("POINTER_ADDRESS").get_text()
        pointer_offsets = self.get_ui_control("POINTER_OFFSETS").get_text()
        output_address = self.get_address(self.get_ui_control("OUTPUT_ADDRESS").get_text())

        ptr = self.process_pointer(pointer_address, pointer_offsets, return_base=True)
        if ptr is None:
            return None
        if output_address < ptr:
            return None
        if output_address - ptr >= 4096:
            return None
        offsets = self.string_to_offsets(pointer_offsets)
        offsets[-1] = output_address - ptr
        return {'pointer': self.get_ui_control("POINTER_ADDRESS").get_text(), 'offsets': self.offsets_to_string(offsets)}
