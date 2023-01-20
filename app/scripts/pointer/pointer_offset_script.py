from app.helpers.exceptions import ScriptException
from app.script_common import SubScript
from app.script_ui import controls
from app.script_ui.validators import address_match, region_match, offsets_match


class PointerOffset(SubScript):
    def build_ui(self, root: controls.Element):
        page: controls.Page = root
        page.add_elements([
            controls.Text("Pointer Address:", width="145px"),
            controls.Input(on_change=self.ctrl_changed, id='PO_INPUT_POINTER_ADDRESS', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='PO_PASTE_POINTER_ADDRESS')])

        page.add_elements([
            controls.Text("Pointer Offsets:", width="125px"),
            controls.Input(on_change=self.ctrl_changed, id='PO_INPUT_POINTER_OFFSETS', trigger_by_focus=False)])

        page.add_elements([
            controls.Text("Output Address:", width="125px"),
            controls.Input(on_change=self.ctrl_changed, id='PO_INPUT_OUTPUT_ADDRESS', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='PO_PASTE_OUTPUT_ADDRESS')])

        page.add_elements([
            controls.Text("Result Address:", width="125px"),
            controls.Input(on_change=None, id='PO_INPUT_RESULT_ADDRESS', trigger_by_focus=False, readonly=True),
            controls.advanced.CopyButton(on_click=self.on_copy, id='PO_COPY_RESULT_ADDRESS')], id='PO_ROW_RESULT_ADDRESS')

        page.add_elements([
            controls.Text("Result Offsets:", width="125px"),
            controls.Input(on_change=None, id='PO_INPUT_RESULT_OFFSETS', trigger_by_focus=False, readonly=True)], id='PO_ROW_RESULT_OFFSETS')

        page.add_elements([controls.Text("Invalid pointer calculated.")], id='PO_ROW_RESULT_INVALID')

    def on_ready(self):
        [self.ui.get_element(x).hide() for x in ['PO_ROW_RESULT_ADDRESS', 'PO_ROW_RESULT_OFFSETS', 'PO_ROW_RESULT_INVALID']]

    def on_start(self):
        [self.ui.get_element(x).set_text("") for x in ['PO_INPUT_POINTER_ADDRESS', 'PO_INPUT_POINTER_OFFSETS', 'PO_INPUT_OUTPUT_ADDRESS']]
        self.on_ready()

    def on_clipboard_copy(self, data):
        address = None
        offsets = None
        if 'address' in data:
            if 'offsets' in data:
                address = data['address']
                offsets = data['offsets']
            else:
                address = data['resolved'] if 'resolved' in data and not data['resolved'].startswith('?') else data['address']
            self.put_data("PO_CLIPBOARD", {'address': address.upper() if ':' not in address else address, 'offsets': offsets})
        self.ui.get_element("PO_PASTE_OUTPUT_ADDRESS").show() if address else self.ui.get_element("PO_PASTE_OUTPUT_ADDRESS").hide()
        self.ui.get_element("PO_PASTE_POINTER_ADDRESS").show() if address else self.ui.get_element("PO_PASTE_POINTER_ADDRESS").hide()

    def on_clipboard_clear(self):
        [self.ui.get_element(x).hide() for x in ['PO_PASTE_OUTPUT_ADDRESS', 'PO_PASTE_POINTER_ADDRESS']]
        self.put_data("PO_CLIPBOARD", None)

    def ctrl_changed(self, name, ele_id, data):
        self.check_for_calculate()

    def on_paste(self, name, ele_id, data):
        cp = self.get_data("PO_CLIPBOARD")
        if name == "PO_PASTE_POINTER_ADDRESS":
            self.ui.get_element("PO_INPUT_POINTER_ADDRESS").set_text(cp['address'])
            if 'offsets' in cp and cp['offsets'] is not None:
                self.ui.get_element("PO_INPUT_POINTER_OFFSETS").set_text(cp['offsets'])
        elif name == "PO_PASTE_OUTPUT_ADDRESS":
            self.ui.get_element("PO_INPUT_OUTPUT_ADDRESS").set_text(cp['address'])
        self.check_for_calculate()


    def on_copy(self, name, ele_id, data):
        pass

    def address_validator(self, txt: str):
        return address_match(txt) or region_match(txt)

    def offsets_validator(self, txt: str):
        return offsets_match(txt)

    def check_for_calculate(self):
        ctrls_lengths = [len(self.ui.get_element(x).get_text()) > 0 for x in ['PO_INPUT_POINTER_ADDRESS', 'PO_INPUT_POINTER_OFFSETS', 'PO_INPUT_OUTPUT_ADDRESS']]
        if not all(ctrls_lengths):
            self.ui.get_element("PO_ROW_RESULT_INVALID").hide()
            return
        if self.address_validator(self.ui.get_element('PO_INPUT_POINTER_ADDRESS').get_text()) and self.address_validator(self.ui.get_element('PO_INPUT_OUTPUT_ADDRESS').get_text()) and self.offsets_validator(
                self.ui.get_element('PO_INPUT_POINTER_OFFSETS').get_text()):
            try:
                pt = self.calculate_pointer()
            except ScriptException:
                pt = None
            if pt is None:
                [self.ui.get_element(ctrl_name).hide() for ctrl_name in ['PO_ROW_RESULT_ADDRESS', 'PO_ROW_RESULT_OFFSETS']]
                self.ui.get_element("PO_ROW_RESULT_INVALID").show()
            else:
                self.ui.get_element("PO_INPUT_RESULT_ADDRESS").set_text(pt['pointer'])
                self.ui.get_element("PO_INPUT_RESULT_OFFSETS").set_text(pt['offsets'])
                [self.ui.get_element(ctrl_name).show() for ctrl_name in ['PO_ROW_RESULT_ADDRESS', 'PO_ROW_RESULT_OFFSETS']]
                self.ui.get_element("PO_ROW_RESULT_INVALID").hide()
            self.put_data("PO_RESULT_POINTER", pt)
        else:
            self.ui.get_element("PO_ROW_RESULT_INVALID").hide()

    def calculate_pointer(self):
        pointer_address = self.ui.get_element("PO_INPUT_POINTER_ADDRESS").get_text()
        pointer_offsets = self.ui.get_element("PO_INPUT_POINTER_OFFSETS").get_text()
        output_address = self.memory_manager.get_address(self.ui.get_element("PO_INPUT_OUTPUT_ADDRESS").get_text())

        ptr = self.memory_manager.read_pointer(pointer_address, pointer_offsets, return_base=True)
        if ptr is None:
            return None
        if output_address < ptr:
            return None
        if output_address - ptr > 0xFFFFF:
            return None
        offsets = self.memory_manager.string_to_offsets(pointer_offsets)
        offsets[-1] = output_address - ptr
        return {'pointer': self.ui.get_element("PO_INPUT_POINTER_ADDRESS").get_text(), 'offsets': self.memory_manager.offsets_to_string(offsets)}
