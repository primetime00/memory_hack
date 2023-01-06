import platform
import re

from app.helpers.data_store import DataStore
from app.helpers.process import get_process_map
from app.script_common import BaseScript
from app.script_ui import BaseUI, Button, Select, Input, Text
from app.search.searcher_multi import SearcherMulti
from app.helpers.directory_utils import scripts_memory_directory
from app.helpers.search_results import SearchResults


class AOBOffset(BaseScript):
    def on_load(self):
        self.put_data("SYSTEM", platform.system())

    def get_name(self):
        return "AOB Offset Tool"

    def get_app(self):
        return []

    def build_ui(self):
        self.add_ui_element(Select("PROCS", "Process", values=[('none', "None")], on_changed=self.ctrl_changed, children=[Button("REFRESH", "Refresh", on_pressed=self.refresh_pid)]))
        self.add_ui_element(Input("AOB_STRING", "AOB", on_changed=self.ctrl_changed, change_on_focus=False, children=[Button("PASTE_AOB", "Paste", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Input("OUTPUT_ADDRESS", "Output Address", on_changed=self.ctrl_changed, change_on_focus=False, children=[Button("PASTE_ADDRESS", "Paste", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Text("RESULT_AOB", "Result AOB Offset", children=[Button("COPY_AOB", "Copy", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Button("CALCULATE_AOB", "Calculate", on_pressed=self.ctrl_pressed))

        self.refresh_pid(self.get_ui_control("PROCS"))

        [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['AOB_STRING', 'OUTPUT_ADDRESS', 'RESULT_AOB', 'PASTE_AOB', 'PASTE_ADDRESS', 'COPY_AOB', 'CALCULATE_AOB']]


    def refresh_pid(self, ele: BaseUI):
        procs = [(x,x) for x in DataStore().get_service('process').get_process_list()]
        procs.insert(0, ('_null', ''))
        self.get_ui_control("PROCS").set_values(procs)

    def on_clipboard_copy(self, data):
        show_paste_aob = False
        show_paste_address = False
        if 'address' in data:
            show_paste_address = True
            if 'resolved' in data and not data['resolved'].startswith('?'):
                self.put_data("CLIPBOARD_ADDRESS", data['resolved'])
                show_paste_address = True
            else:
                self.put_data("CLIPBOARD_ADDRESS", data['address'])
        if 'aob' in data:
            self.put_data("CLIPBOARD_AOB", data['aob'])
            show_paste_aob = True
        self.get_ui_control("PASTE_AOB").show() if show_paste_aob else self.get_ui_control("PASTE_AOB").hide()
        self.get_ui_control("PASTE_ADDRESS").show() if show_paste_address else self.get_ui_control("PASTE_ADDRESS").hide()


    def on_clipboard_clear(self):
        self.get_ui_control("PASTE_AOB").hide()
        self.get_ui_control("PASTE_ADDRESS").hide()

    def ctrl_changed(self, ele: BaseUI, value):
        if ele.get_name() == 'AOB_STRING' or ele.get_name() == 'OUTPUT_ADDRESS':
            self.check_for_calculate()
        elif ele.get_name() == 'PROCS':
            DataStore().get_service('script').set_app(self.get_ui_control("PROCS").get_selection())
            self.put_data('APP_NAME', self.get_ui_control("PROCS").get_selection())
            if value != '_null':
                [self.get_ui_control(ctrl_name).show() for ctrl_name in ['AOB_STRING', 'OUTPUT_ADDRESS']]
                self.put_data("PROCESS_MAP", get_process_map(self.get_memory()))
            else:
                [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['AOB_STRING', 'OUTPUT_ADDRESS', 'RESULT_AOB', 'PASTE_AOB', 'PASTE_ADDRESS', 'COPY_AOB', 'CALCULATE_AOB']]

    def check_for_calculate(self):
        aob = self.get_ui_control('AOB_STRING').get_text()
        addr = self.get_ui_control('OUTPUT_ADDRESS').get_text()
        if len(addr) == 0 or len(aob) == 0:
            self.get_ui_control('CALCULATE_AOB').hide()
            return
        if not self.address_validator(addr):
            self.get_ui_control('CALCULATE_AOB').hide()
            return
        if not self.aob_validator(aob):
            self.get_ui_control('CALCULATE_AOB').hide()
            return
        self.get_ui_control('CALCULATE_AOB').show()

    def ctrl_pressed(self, ele: BaseUI):
        if ele.get_name() == 'CALCULATE_AOB':
            self.calculate_aob()
        elif ele.get_name() == 'PASTE_AOB':
            self.get_ui_control("AOB_STRING").set_text(self.get_data("CLIPBOARD_AOB"))
            self.check_for_calculate()
        elif ele.get_name() == 'PASTE_ADDRESS':
            self.get_ui_control("OUTPUT_ADDRESS").set_text(self.get_data("CLIPBOARD_ADDRESS"))
            self.check_for_calculate()
        elif ele.get_name() == 'COPY_AOB':
            res_aob = self.get_data("RESULT_DATA")
            ele.update_queue.put({'op': "script", 'data': {'script': 'document.clipboard.copy({{"aob": "{}", "offset": "{:X}"}})'.format(res_aob['aob'], res_aob['offset'])}})

    def address_validator(self, txt: str):
        if re.match(self.re_fn, txt.upper().strip(), re.IGNORECASE) or re.match(self.re_addr, txt.upper().strip(), re.IGNORECASE):
            return True
        return False

    def aob_validator(self, txt: str):
        if re.match(self.re_aob, txt.upper().strip(), re.IGNORECASE):
            return True
        return False

    def is_linux(self):
        return self.get_data("SYSTEM") == 'Linux'

    def calculate_aob(self):
        aob = self.get_ui_control('AOB_STRING').get_text()
        addr = int(self.get_ui_control('OUTPUT_ADDRESS').get_text(), 16)
        if not self.get_data("SEARCHER"):
            self.put_data("SEARCHER", SearcherMulti(self.get_memory(), directory=scripts_memory_directory, results=SearchResults(db_path=scripts_memory_directory.joinpath("aob_offset.db"))))
        searcher: SearcherMulti = self.get_data("SEARCHER")
        [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['RESULT_AOB', 'PASTE_AOB', 'PASTE_ADDRESS', 'COPY_AOB']]
        [self.get_ui_control(ctrl_name).disable() for ctrl_name in ['AOB_STRING', 'OUTPUT_ADDRESS', 'CALCULATE_AOB']]
        searcher.set_search_size("array")
        searcher.search_memory_value(aob)
        [self.get_ui_control(ctrl_name).show() for ctrl_name in ['RESULT_AOB', 'PASTE_AOB', 'PASTE_ADDRESS']]
        if len(searcher.results) == 0:
            self.get_ui_control("RESULT_AOB").set_text("Could not find AOB in memory.")
        else:
            min_item = 0xFF
            min_distance = 0x7FFFFFFFFFFFFFFF
            res = searcher.get_results(limit=4)
            for i in range(0, len(res)):
                cr = res[i]
                dist = abs(addr - cr['address'])
                if dist < min_distance:
                    min_distance = dist
                    min_item = i
            self.get_ui_control("RESULT_AOB").set_text("Result Offset: {:X}".format(res[min_item]['address'] - addr))
            self.put_data("RESULT_DATA", {'aob': aob, 'offset': addr - res[min_item]['address']})
            [self.get_ui_control(ctrl_name).show() for ctrl_name in ['COPY_AOB']]
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['AOB_STRING', 'OUTPUT_ADDRESS', 'CALCULATE_AOB']]