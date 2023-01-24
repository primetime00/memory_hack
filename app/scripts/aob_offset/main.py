import platform

from app.script_common import BaseScript
from app.script_ui import controls
from app.script_ui.validators import address_match, aob_match
from app.search.searcher_multi import SearcherMulti


class AOBOffset(BaseScript):
    def on_load(self):
        self.put_data("SYSTEM", platform.system())

    def get_script_information(self):
        return {
            'title': "AOB Offset Tool",
            'author': "Ryan Kegel",
            'version': '1.0.0'}

    def build_ui(self):
        ps_page = self.ui.add_page(controls.Page())
        main_page = self.ui.add_page(controls.Page(id='MAIN_PAGE'))
        ps_page.add_elements([controls.advanced.ProcessSelect(self.process_selected, id='PROCS')])
        self.ui.set_page_header(ps_page, "Process Select")
        self.ui.set_page_header(main_page, "AOB Offset")

        main_page.add_elements([
            controls.Text("AOB:", width="40px"),
            controls.Input(on_change=self.ctrl_changed, id='AOB_STRING', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='AOB_PASTE')])

        main_page.add_elements([
            controls.Text("Output Address:", width="125px"),
            controls.Input(on_change=self.ctrl_changed, id='OUTPUT_ADDRESS', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='OUTPUT_ADDRESS_PASTE')])

        main_page.add_element(ResultRow(id='RESULT_ROW', ctrl_changed=self.ctrl_changed, ctrl_clicked=self.ctrl_clicked, on_copy=self.on_copy))

    def on_ready(self):
        self.ui.get_element("MAIN_PAGE").hide()
        [self.ui.get_element(x).hide() for x in ['AOB_PASTE', 'OUTPUT_ADDRESS_PASTE']]

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
            self.check_for_calculate()
        if name == 'OUTPUT_ADDRESS_PASTE':
            self.ui.get_element("OUTPUT_ADDRESS").set_text(self.get_data("CLIPBOARD")['address'].upper())
            self.check_for_calculate()

    def on_copy(self, name: str, ele_id: str, data):
        res = self.get_data("RESULT_DATA")
        self.ui.get_element("COPY_BUTTON").copy({'aob': res['aob'], 'offset': '{:X}'.format(res['offset'])})


    def ctrl_changed(self, name: str, ele_id: str, data):
        if name == 'AOB_STRING' or name == 'OUTPUT_ADDRESS':
            self.check_for_calculate()

    def on_clipboard_copy(self, data):
        address = None
        aob = None
        if 'address' in data:
            address = data['resolved'] if 'resolved' in data and not data['resolved'].startswith('?') else data['address']
        if 'aob' in data:
            aob = data['aob']
        self.put_data("CLIPBOARD", {'aob': aob, 'address': address})
        self.ui.get_element("AOB_PASTE").show() if aob else self.ui.get_element("AOB_PASTE").hide()
        self.ui.get_element("OUTPUT_ADDRESS_PASTE").show() if address else self.ui.get_element("OUTPUT_ADDRESS_PASTE").hide()


    def on_clipboard_clear(self):
        self.ui.get_element("AOB_PASTE").hide()
        self.ui.get_element("OUTPUT_ADDRESS_PASTE").hide()

    def check_for_calculate(self):
        aob = self.ui.get_element('AOB_STRING').get_text()
        addr = self.ui.get_element('OUTPUT_ADDRESS').get_text()
        if len(addr) == 0 or len(aob) == 0:
            self.ui.get_element("RESULT_ROW").ready_no_calculate()
            return
        if not self.address_validator(addr):
            self.ui.get_element("RESULT_ROW").ready_no_calculate()
            return
        if not self.aob_validator(aob):
            self.ui.get_element("RESULT_ROW").ready_no_calculate()
            return
        self.ui.get_element("RESULT_ROW").ready_for_calculate()

    def ctrl_clicked(self, name: str, ele_id: str, data):
        if name == 'CALCULATE_AOB':
            self.calculate_aob()

    def address_validator(self, txt: str):
        return address_match(txt)

    def aob_validator(self, txt: str):
        return aob_match(txt)

    def is_linux(self):
        return self.get_data("SYSTEM") == 'Linux'

    def calculate_aob(self):
        aob = self.ui.get_element('AOB_STRING').get_text()
        addr = int(self.ui.get_element('OUTPUT_ADDRESS').get_text(), 16)

        searcher: SearcherMulti = self.memory_manager.get_searcher()

        self.ui.get_element("RESULT_ROW").hide()
        searcher.set_search_size("array")
        searcher.search_memory_value(aob)

        if len(searcher.results) == 0:
            self.ui.get_element("RESULT_ROW").ready_no_result()
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
            self.ui.get_element("RESULT_OFFSET").set_text("{:X}".format(res[min_item]['address'] - addr))
            self.put_data("RESULT_DATA", {'aob': aob, 'offset': addr - res[min_item]['address']})
            self.ui.get_element("RESULT_ROW").ready_valid_result()
        #[self.ui.get_element(ctrl_name).enable() for ctrl_name in ['AOB_STRING', 'OUTPUT_ADDRESS', 'CALCULATE_AOB']]

class ResultRow(controls.Row):
    def __init__(self, ctrl_clicked: callable, ctrl_changed: callable, on_copy: callable, **kwargs):
        super().__init__(**kwargs)
        self.ctrl_clicked = ctrl_clicked
        self.ctrl_changed = ctrl_changed
        self.on_copy = on_copy
        self.build_ui()

    def build_ui(self):
        result_calculate_button_row = controls.Row()
        result_calculate_button_row.add_element(controls.Button("Calculate", on_click=self.ctrl_clicked, id='CALCULATE_AOB'))

        result_status_row = controls.Row(id='STATUS_ROW')
        result_status_row.add_element(controls.Text("Could not find AOB.", id='AOB_STATUS'))

        result_offset_row = controls.Row(id='OFFSET_ROW').add_elements([
            controls.Text("Result Offset:", width="125px"),
            controls.Input(on_change=self.ctrl_changed, readonly=True, id='RESULT_OFFSET'),
            controls.advanced.CopyButton(on_click=self.on_copy, id='COPY_BUTTON')])

        self.add_element(result_calculate_button_row)
        self.add_element(result_status_row)
        self.add_element(result_offset_row)

    def on_ready(self):
        self.hide()
        self.get_element('OFFSET_ROW').hide()
        self.get_element('STATUS_ROW').hide()
        self.get_element('CALCULATE_AOB').show()


    def ready_for_calculate(self):
        self.show()

    def ready_no_calculate(self):
        self.hide()
        self.get_element('OFFSET_ROW').hide()
        self.get_element('STATUS_ROW').hide()


    def ready_valid_result(self):
        self.get_element('OFFSET_ROW').show()
        self.get_element('STATUS_ROW').hide()
        self.show()

    def ready_no_result(self):
        self.get_element('OFFSET_ROW').hide()
        self.get_element('STATUS_ROW').show()
        self.show()

    def process_deselected(self):
        self.get_element('OFFSET_ROW').hide()
        self.get_element('STATUS_ROW').hide()


