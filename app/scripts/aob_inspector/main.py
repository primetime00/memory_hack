import ctypes
import platform

from typing import cast
from app.script_common import BaseScript
from app.script_ui import controls
from app.script_ui.validators import address_match, aob_match, offset_match
from app.search.searcher_multi import SearcherMulti
from .aob_result import AOBResultControl


class AOBInspect(BaseScript):
    def on_load(self):
        self.put_data("SYSTEM", platform.system())
        self.put_data("LOOPING", False)

    def get_script_information(self):
        return {
            'title': "AOB Inspector",
            'author': "Ryan Kegel",
            'version': '1.0.0'}

    def build_ui(self):
        ps_page = self.ui.add_page(controls.Page())
        main_page = self.ui.add_page(controls.Page(id='MAIN_PAGE'))
        ps_page.add_elements([controls.advanced.ProcessSelect(self.process_selected, id='PROCS')])
        self.ui.set_page_header(ps_page, "Process Select")
        self.ui.set_page_header(main_page, "AOB Inspection")

        main_page.add_elements([
            controls.Text("AOB:", width="100px"),
            controls.Input(on_change=self.ctrl_changed, id='AOB_STRING', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='AOB_PASTE')])

        main_page.add_elements([
            controls.Text("Offset:", width="100px"),
            controls.Input(on_change=self.ctrl_changed, id='OFFSET_STRING', trigger_by_focus=False)])

        main_page.add_elements([
            controls.Text("Known Addresses:", width="100px"),
            controls.Input(on_change=self.ctrl_changed, id='KNOWN_ADDRESSES_STRING', trigger_by_focus=False)])

        main_page.add_elements([
            controls.Space(width="100px"),
            controls.Button("Inspect", on_click=self.ctrl_clicked, id='BUTTON_INSPECT'),
            controls.Button("Stop", on_click=self.ctrl_clicked, id='BUTTON_STOP')])

        main_page.add_element(AOBResultControl(id='RESULT_ROW', on_copy=self.on_copy, on_count=self.count_aob))

    def on_ready(self):
        self.ui.get_element("MAIN_PAGE").hide()
        [self.ui.get_element(x).hide() for x in ['AOB_PASTE']]
        self.ui.get_element('BUTTON_INSPECT').hide()
        self.ui.get_element('BUTTON_STOP').hide()

    def process_selected(self, proc):
        if proc is None:
            self.ui.get_element("MAIN_PAGE").hide()
            self.ui.get_element("RESULT_ROW").process_deselected()
            self.put_data("RESULT_DATA", None)
        else:
            self.ui.get_element("MAIN_PAGE").show()
            self.check_for_calculate()

    def on_paste(self, name: str, ele_id: str, data):
        if name == 'AOB_PASTE':
            self.ui.get_element("AOB_STRING").set_text(self.get_data("CLIPBOARD")['aob'].upper())
            self.ui.get_element("OFFSET_STRING").set_text(self.get_data("CLIPBOARD")['offset'].upper())
            addr_string = ""
            for addr in self.get_data("CLIPBOARD")['addresses']:
                addr_string += '{:X}, '.format(addr)
            self.ui.get_element("KNOWN_ADDRESSES_STRING").set_text(addr_string[0:-2])
            self.check_for_calculate()

    def on_copy(self, name: str, ele_id: str, data):
        res = self.get_data("RESULT_DATA")
        self.ui.get_element("COPY_BUTTON").copy({'aob': res['aob'], 'offset': '{:X}'.format(res['offset'])})


    def ctrl_changed(self, name: str, ele_id: str, data):
        if name == 'AOB_STRING' or name == 'OFFSET_STRING' or name == 'KNOWN_ADDRESSES_STRING':
            self.check_for_calculate()

    def on_clipboard_copy(self, data):
        addresses = []
        aob = None
        offset = None
        if 'last_addresses' in data and data['last_addresses']:
            addresses = data['last_addresses']
        if 'aob' in data:
            aob = data['aob']
        if 'offset' in data:
            offset = data['offset']
        if addresses and aob and data:
            self.put_data("CLIPBOARD", {'aob': aob, 'addresses': addresses, 'offset': offset})
        self.ui.get_element("AOB_PASTE").show() if addresses and aob and data else self.ui.get_element("AOB_PASTE").hide()


    def on_clipboard_clear(self):
        self.ui.get_element("AOB_PASTE").hide()

    def check_for_calculate(self):
        aob = self.ui.get_element('AOB_STRING').get_text()
        offset = self.ui.get_element('OFFSET_STRING').get_text()
        addrs = self.ui.get_element('KNOWN_ADDRESSES_STRING').get_text()
        if len(addrs) == 0 or len(aob) == 0 or len(offset) == 0:
            self.ui.get_element("RESULT_ROW").hide()
            return
        addresses = [x.strip() for x in addrs.split(',')]
        if not all(self.address_validator(addr) for addr in addresses) or not self.aob_validator(aob) or not self.offset_validator(offset):
            self.ui.get_element("BUTTON_INSPECT").hide()
            self.ui.get_element("RESULT_ROW").hide()
            return
        self.ui.get_element("BUTTON_INSPECT").show()

    def ctrl_clicked(self, name: str, ele_id: str, data):
        if name == 'BUTTON_INSPECT':
            self.put_data("AOB_LENGTH", len(self.ui.get_element('AOB_STRING').get_text().split(' ')))
            self.put_data("AOB_STRING", self.ui.get_element('AOB_STRING').get_text())
            self.put_data("ADDRESSES", [int(addr.strip(), 16) for addr in self.ui.get_element('KNOWN_ADDRESSES_STRING').get_text().split(',')])
            cast(AOBResultControl, self.ui.get_element("RESULT_ROW")).set_aob(self.get_data("AOB_STRING"), self.ui.get_element('OFFSET_STRING').get_text(), self.get_data("ADDRESSES"))
            self.ui.get_element('AOB_STRING').disable()
            self.ui.get_element('OFFSET_STRING').disable()
            self.ui.get_element('KNOWN_ADDRESSES_STRING').disable()
            self.inspect()
            self.ui.get_element('BUTTON_STOP').show()
            self.ui.get_element('BUTTON_INSPECT').hide()
            self.put_data("LOOPING", True)
        elif name == 'BUTTON_STOP':
            self.put_data("LOOPING", False)
            self.ui.get_element('BUTTON_STOP').hide()
            self.ui.get_element('AOB_STRING').enable()
            self.ui.get_element('OFFSET_STRING').enable()
            self.ui.get_element('KNOWN_ADDRESSES_STRING').enable()
            self.ui.get_element('BUTTON_INSPECT').show()



    def address_validator(self, txt: str):
        return address_match(txt)

    def aob_validator(self, txt: str):
        return aob_match(txt)

    def offset_validator(self, txt: str):
        return offset_match(txt)

    def inspect(self):
        data_len = self.get_data("AOB_LENGTH")
        addrs = self.get_data("ADDRESSES")
        for addr in addrs:
            data = self.memory_manager.memory.read_memory(addr, (ctypes.c_uint8*data_len)())
            cast(AOBResultControl, self.ui.get_element("RESULT_ROW")).set_read(data, addr)
        self.ui.get_element("RESULT_ROW").show()

    def frame(self):
        if self.get_data("LOOPING"):
            self.inspect()

    def count_aob(self, addr:int, aob:str):
        searcher = self.memory_manager.get_searcher("AOBI_COUNTER")
        searcher.set_search_size('array')
        searcher.search_memory_value(aob)
        return len(searcher.get_results())
