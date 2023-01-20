import platform

from app.script_common import TopScript
from app.script_ui import controls
from .pointer_offset_script import PointerOffset
from .pointer_scanner_script import PointerScanner
from .pointer_verify_script import PointerVerify


class Pointer(TopScript):
    def on_load(self):
        self.add_script(PointerOffset(id='POINTER_OFFSET_SCRIPT'))
        self.add_script(PointerScanner(id='POINTER_SCANNER_SCRIPT'))
        self.add_script(PointerVerify(id='POINTER_VERIFY_SCRIPT'))
        self.put_data("SYSTEM", platform.system())
        self.put_data("APP_NAME", "unknown")


    def get_script_information(self):
        return {
            'title': "Pointer Tools",
            'author': "Ryan Kegel",
            'version': '1.0.0'}

    def build_ui(self):
        process_select_page = self.ui.add_page(controls.Page())
        process_select_page.add_elements([controls.advanced.ProcessSelect(self.process_selected, id='PROCS')])

        pointer_offset_page = self.ui.add_page(controls.Page(id='PAGE_POINTER_OFFSET'))
        self.get_script("POINTER_OFFSET_SCRIPT").build_ui(pointer_offset_page)

        pointer_scanner_page = self.ui.add_page(controls.Page(id='PAGE_POINTER_SCANNER'))
        self.get_script("POINTER_SCANNER_SCRIPT").build_ui(pointer_scanner_page)

        pointer_verify_page = self.ui.add_page(controls.Page(id='PAGE_POINTER_VERIFY'))
        self.get_script("POINTER_VERIFY_SCRIPT").build_ui(pointer_verify_page)

        menu_page = self.ui.add_page(controls.Page(id='PAGE_MENU'))
        menu_page.add_elements([
            controls.Button("Pointer Scanner", self.menu_button_clicked, True, align_text='center', id='BUTTON_POINTER_SCANNER_PAGE')
        ])
        menu_page.add_elements([
            controls.Button("Pointer Verify", self.menu_button_clicked, True, align_text='center', id='BUTTON_POINTER_VERIFY_PAGE')
        ])
        menu_page.add_elements([
            controls.Button("Pointer Offset", self.menu_button_clicked, True, align_text='center', id='BUTTON_POINTER_OFFSET_PAGE')
        ])

        back_page = self.ui.add_page(controls.Page(id='PAGE_BACK'))
        back_page.add_elements([
            controls.Button("Back", self.menu_button_clicked, True, id='BUTTON_BACK')
        ])

    def on_ready(self):
        self.ui.get_element('PAGE_POINTER_OFFSET').hide()
        self.ui.get_element('PAGE_POINTER_SCANNER').hide()
        self.ui.get_element('PAGE_POINTER_VERIFY').hide()
        self.ui.get_element('PAGE_BACK').hide()
        self.ui.get_element('PAGE_MENU').hide()


    def process_selected(self, proc):
        if proc is None:
            self.ui.get_element('PAGE_POINTER_SCANNER').hide()
            self.ui.get_element('PAGE_POINTER_OFFSET').hide()
            self.ui.get_element('PAGE_POINTER_VERIFY').hide()
            self.ui.get_element('PAGE_BACK').hide()
            self.ui.get_element('PAGE_MENU').hide()
            self.put_data("APP_NAME", 'unknown')
        else:
            self.put_data("APP_NAME", proc)
            self.ui.get_element("PAGE_MENU").show()

    def menu_button_clicked(self, name: str, ele_id, data):
        if name == 'BUTTON_POINTER_OFFSET_PAGE':
            self.get_script("POINTER_OFFSET_SCRIPT").on_start()
            self.ui.get_element('PAGE_POINTER_OFFSET').show()
            self.ui.get_element('PAGE_MENU').hide()
            self.ui.get_element('PAGE_BACK').show()
            self.put_data("APP", None)
        elif name == 'BUTTON_POINTER_SCANNER_PAGE':
            self.get_script("POINTER_SCANNER_SCRIPT").on_start()
            self.ui.get_element('PAGE_POINTER_SCANNER').show()
            self.ui.get_element('PAGE_MENU').hide()
            self.ui.get_element('PAGE_BACK').show()
            self.put_data("APP", None)
        elif name == 'BUTTON_POINTER_VERIFY_PAGE':
            self.get_script("POINTER_VERIFY_SCRIPT").on_start()
            self.ui.get_element('PAGE_POINTER_VERIFY').show()
            self.ui.get_element('PAGE_MENU').hide()
            self.ui.get_element('PAGE_BACK').show()
            self.put_data("APP", None)
        elif name == 'BUTTON_BACK':
            [script.on_exit() for script in self.subscripts.values()]
            self.ui.get_element('PAGE_POINTER_OFFSET').hide()
            self.ui.get_element('PAGE_POINTER_SCANNER').hide()
            self.ui.get_element('PAGE_POINTER_VERIFY').hide()
            self.ui.get_element('PAGE_BACK').hide()
            self.ui.get_element('PAGE_MENU').show()

    def is_linux(self):
        return self.get_data("SYSTEM") == 'Linux'