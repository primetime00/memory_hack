from app.script_ui._base import BaseUI

class Button(BaseUI):
    pressed = False

    def ui_data(self):
        return '<ons-button id="{}" class="script_control" onclick="script.script_interact_button(event)">Go</ons-button>{}'.format(self.id, self.title)

    def handle_interaction(self, data):
        self.pressed = True

    def process(self):
        if self.pressed:
            self.pressed = False
            self.int_callback()



