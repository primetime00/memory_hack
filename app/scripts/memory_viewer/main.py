import ctypes
import platform
from typing import cast

from app.script_common import BaseScript
from app.script_ui import controls
from app.script_ui.validators import address_match, region_match
from .memory_viewer import MemoryControl


class MemoryViewer(BaseScript):
    def on_load(self):
        self.put_data("SYSTEM", platform.system())
        self.put_data("ADDRESS", 0)
        self.put_data("ADDRESS_TEXT", '')
        self.ui.add_style(".flash {\
                -webkit-animation-name: flash-animation;\
                -webkit-animation-duration: 0.3s;\
                animation-name: flash-animation;\
                animation-duration: 0.3s;\
            }\
            @-webkit-keyframes flash-animation {\
                from { background: yellow; }\
                to   { background: default; }\
            }\
            @keyframes flash-animation {\
                from { background: yellow; }\
                to   { background: default; }\
            }")

    def get_script_information(self):
        return {
            'title': "Memory Viewer",
            'author': "Ryan Kegel",
            'version': '1.0.0'}

    def build_ui(self):
        ps_page = self.ui.add_page(controls.Page())
        main_page = self.ui.add_page(controls.Page(id='MAIN_PAGE'))
        memory_page = self.ui.add_page(controls.Page(id='MEMORY_PAGE'))
        ps_page.add_elements([controls.advanced.ProcessSelect(self.process_selected, id='PROCS')])
        self.ui.set_page_header(ps_page, "Process Select")
        self.ui.set_page_header(main_page, "Address Location")
        self.ui.set_page_header(memory_page, "Memory")

        main_page.add_elements([
            controls.Text("Address:", width="17%"),
            controls.Input(on_change=self.ctrl_changed, id='ADDRESS_STRING', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='ADDRESS_PASTE')])

        memory_page.add_elements([
            MemoryControl(None, self.write, self.direction_pressed, id="MEMORY_CONTROL")
        ])

    def on_ready(self):
        self.ui.get_element("MAIN_PAGE").hide()
        self.ui.get_element("MEMORY_PAGE").hide()
        [self.ui.get_element(x).hide() for x in ['ADDRESS_PASTE']]

    def process_selected(self, proc):
        if proc is None:
            self.ui.get_element("MAIN_PAGE").hide()
            self.ui.get_element("MEMORY_PAGE").hide()
            self.put_data("RESULT_DATA", None)
        else:
            self.ui.get_element("MAIN_PAGE").show()
            #self.ui.get_element("MEMORY_PAGE").show()
            pass

    def frame(self):
        addr_string = self.ui.get_element("ADDRESS_STRING").get_text()
        if addr_string != self.get_data("ADDRESS_TEXT"):
            self.put_data("ADDRESS_TEXT", addr_string)
            if (address_match(addr_string) or region_match(addr_string)) and self.memory_manager.get_base(addr_string):
                addr = self.memory_manager.get_address(addr_string)
            else:
                addr = None
            if addr != self.get_data("ADDRESS"):
                self.put_data("ADDRESS", addr)
                if addr is None:
                    self.ui.get_element("MEMORY_PAGE").hide()
                else:
                    cast(MemoryControl, self.ui.get_element('MEMORY_CONTROL')).clear_data()
                    self.ui.get_element("MEMORY_PAGE").show()

        if self.get_data("ADDRESS"):
            self.get_memory_bytes(self.get_data("ADDRESS"), cast(MemoryControl, self.ui.get_element("MEMORY_CONTROL")).get_count())



    def on_paste(self, name: str, ele_id: str, data):
        if name == 'ADDRESS_PASTE':
            self.ui.get_element("ADDRESS_STRING").set_text(self.get_data("CLIPBOARD")['address'].upper())
            pass

    def ctrl_changed(self, name: str, ele_id: str, data):
        if name == 'AOB_STRING' or name == 'OUTPUT_ADDRESS':
            pass

    def on_clipboard_copy(self, data):
        address = None
        if 'address' in data:
            address = data['resolved'] if 'resolved' in data and not data['resolved'].startswith('?') else data['address']
        self.put_data("CLIPBOARD", {'address': address})
        self.ui.get_element("ADDRESS_PASTE").show() if address else self.ui.get_element("ADDRESS_PASTE").hide()


    def on_clipboard_clear(self):
        self.ui.get_element("ADDRESS_PASTE").hide()

    def ctrl_clicked(self, name: str, ele_id: str, data):
        if name == 'CALCULATE_AOB':
            pass

    def is_linux(self):
        return self.get_data("SYSTEM") == 'Linux'

    def get_memory_bytes(self, address: int, size: int):
        data = (ctypes.c_ubyte * size)()
        self.memory_manager.memory.read_memory(address, data)
        cast(MemoryControl, self.ui.get_element('MEMORY_CONTROL')).set_data(bytes(data), address=address)

    def write(self, addr: int, val):
        self.memory.write_memory(addr, val)

    def direction_pressed(self, direction:str, count: int):
        addr = self.get_data("ADDRESS")
        bounds = self.memory_manager.get_base_bounds("{:x}".format(addr))
        if direction == 'up':
            addr -= count
            if addr < bounds[0]:
                addr = bounds[0]
        else:
            addr += count
            if addr+count >= bounds[1]:
                addr = bounds[1] - count
        self.ui.get_element("ADDRESS_STRING").set_text('{:X}'.format(addr))
