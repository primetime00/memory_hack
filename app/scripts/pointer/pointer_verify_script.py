import ctypes
import json
from pathlib import Path

from app.script_common import SubScript
from app.script_common.memory import MemoryManager
from app.script_ui import controls
from app.script_ui.validators import address_match


class PointerVerify(SubScript):

    def get_directory_name(self):
        return 'pointerscanner'

    def build_ui(self, root: controls.Element):
        page: controls.Page = root
        page.add_elements([
            controls.Text("Pointer File:", width="125px"),
            controls.Select(values=[('none', 'None')], on_change=self.ctrl_changed, id='PV_SELECT_POINTER_FILE')])

        page.add_elements([
            controls.Text("Current Address:", width="125px"),
            controls.Input(on_change=self.ctrl_changed, id='PV_INPUT_CURRENT_ADDRESS', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='PV_PASTE_CURRENT_ADDRESS')])

        page.add_elements([controls.Button("Verify", on_click=self.start_verify, id='PV_BUTTON_VERIFY')], id='PV_ROW_START_VERIFY')

        page.add_elements([
            controls.Text("Number of Results:", width="145px"),
            controls.Text("[unknown]", id='PV_TEXT_NUMBER_OF_RESULTS')], id='PV_ROW_NUMBER_OF_RESULTS')

        page.add_elements([
            self.PointerResultGroup(id='PV_GROUP_RESULTS')], id='PV_ROW_RESULTS')

    def on_ready(self):
        [self.ui.get_element(x).hide() for x in ['PV_ROW_NUMBER_OF_RESULTS', 'PV_ROW_RESULTS']]
        [self.ui.get_element(x).disable() for x in ['PV_BUTTON_VERIFY']]

    def on_start(self):
        [self.ui.get_element(x).set_text("") for x in ['PV_INPUT_CURRENT_ADDRESS']]
        self.ui.get_element('PV_SELECT_POINTER_FILE').set_values(self.get_pointer_files())
        self.on_ready()

    def on_clipboard_copy(self, data):
        address = None
        if 'address' in data:
            address = data['resolved'] if 'resolved' in data and not data['resolved'].startswith('?') else data['address']
            if ':' in address:
                address = None
            else:
                self.put_data("PV_CLIPBOARD", {'address': address.upper()})
        self.ui.get_element("PV_PASTE_CURRENT_ADDRESS").show() if address else self.ui.get_element("PV_PASTE_CURRENT_ADDRESS").hide()

    def on_clipboard_clear(self):
        [self.ui.get_element(x).hide() for x in ['PV_PASTE_CURRENT_ADDRESS']]
        self.put_data("PV_CLIPBOARD", None)

    def ctrl_changed(self, name, ele_id, data):
        self.check_for_verify()

    def on_paste(self, name, ele_id, data):
        cp = self.get_data("PV_CLIPBOARD")
        if name == "PV_PASTE_CURRENT_ADDRESS":
            self.ui.get_element("PV_INPUT_CURRENT_ADDRESS").set_text(cp['address'])
        self.check_for_verify()

    def on_copy(self, name, ele_id, data):
        pass

    def address_validator(self, txt: str):
        return address_match(txt)

    def verify_complete(self, valid_pointers: list):
        num_results = len(valid_pointers)
        self.ui.get_element("PV_TEXT_NUMBER_OF_RESULTS").set_text('<strong>{}</strong>'.format(num_results))
        self.ui.get_element("PV_ROW_NUMBER_OF_RESULTS").show()
        if num_results > 0:
            self.ui.get_element("PV_GROUP_RESULTS").set_pointers(valid_pointers[0:50], self.memory_manager)
            self.ui.get_element("PV_GROUP_RESULTS").render()
            self.ui.get_element("PV_ROW_RESULTS").show()
        else:
            self.ui.get_element("PV_ROW_RESULTS").hide()



    def check_for_verify(self):
        addr = self.ui.get_element("PV_INPUT_CURRENT_ADDRESS").get_text()
        fname = self.ui.get_element("PV_SELECT_POINTER_FILE").get_selection()
        if len(addr) == 0 or not self.address_validator(addr) or not Path(self.get_directory()).joinpath(fname).exists():
            self.ui.get_element("PV_BUTTON_VERIFY").disable()
            return
        self.ui.get_element("PV_BUTTON_VERIFY").enable()

    def get_pointer_files(self):
        _dir = Path(self.get_directory())
        files = [(p.name, p.name) for p in _dir.glob("*.ptr")]
        if not files:
            files = [('_null', '')]
        return files

    def _find_address(self, ptr):
        for process in self.memory_manager.get_process_map():
            if process['pathname'] == ptr['path'] and process['map_index'] == ptr['node']:
                return process['start'] + ptr['base_offset']
        return None

    def start_verify(self, name, ele_id, data):
        current_address = int(self.ui.get_element("PV_INPUT_CURRENT_ADDRESS").get_text(), 16)
        ptr_file = Path(self.get_directory()).joinpath(self.ui.get_element("PV_SELECT_POINTER_FILE").get_selection())
        with ptr_file.open(mode='rt') as f:
            orig_data = json.load(f)
        data = orig_data.copy()

        pointers = []
        for item in data:
            new_address = self._find_address(item)
            if new_address:
                new_item = item.copy()
                new_item['address'] = new_address
                pointers.append(new_item)

        valid_pointers = []
        for pointer in pointers:
            address = pointer['address']
            try:
                for offset in pointer['offsets']:
                    read = self.get_memory().read_memory(address, ctypes.c_uint64()).value
                    read = read + offset
                    address = read
                if address == current_address:
                    valid_pointers.append(pointer)
            except Exception:
                continue
        self.verify_complete(valid_pointers)

    def get_pointer_list_html(self, valid_pointers):
        html ='hello'
        for pt in valid_pointers:
            html += 'yo'
        return html

    class PointerResultGroup(controls.Group):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.pointers = {}
            self.mm: MemoryManager = None
            self.html: str = ""

        def handle_interaction(self, _id: str, data):
            pointer_copy_data = self.mm.copy_pointer(self.pointers[_id])
            self.update_queue.put({'op': "script", 'data': {'script': 'document.clipboard.copy({})'.format(json.dumps(pointer_copy_data))}})


        def set_pointers(self, pointers: list, memory_manager: MemoryManager):
            self.mm = memory_manager
            html = '<ons-list>'
            for index in range(0, len(pointers)):
                p = pointers[index]
                key = '{}_button-{:03}'.format(self.script_ids[-1], index)
                self.pointers[key] = p
                addr_str = '{:X}'.format(p['address'])
                off_str = memory_manager.offsets_to_string(p['offsets'])
                html += '<ons-list-item>'\
                        '<ons-row vertical-align="center">{}' \
                        '</ons-row>' \
                        '<ons-row vertical-align="center">' \
                            '<ons-col align="center" class="col ons-col-inner" style="padding-left:10px;">{}</ons-col>' \
                            '<ons-col align="center" class="col ons-col-inner" width="60px">' \
                                '<ons-button id="{}" onclick="script.script_interact_button(event)"><ons-icon icon="md-copy"/>' \
                                '</ons-button>' \
                            '</ons-col>' \
                        '</ons-row>' \
                        '</ons-list-item>\n'.format(memory_manager.get_base(addr_str), off_str, key)
            html += '</ons-list>'
            self.html = html

        def render(self):
            self.inner(self.html)












