from mem_edit import Process
from app.script_ui._base import BaseUI

class Toggle(BaseUI):
    def __init__(self, title, interact_callback, enable_checker=None, input_handler=None, on=False):
        super().__init__(title, interact_callback, enable_checker, input_handler)
        self.toggled = on

    def handle_interaction(self, data):
        self.toggled = data['checked']

    def ui_data(self):
        return '<ons-switch id="{}" class="script_control" onchange="script.script_interact_toggle(event)" {}></ons-switch>{}'.format(self.id, ("checked" if self.toggled else ""), self.title)

    def process(self):
        if self.toggled:
            self.int_callback()

