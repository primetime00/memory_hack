from app.script_ui._base import BaseUI

class Button(BaseUI):

    def __init__(self, name: str, title: str , on_pressed: callable = None, enable_checker:callable = None, children=None):
        super().__init__(name, title, enable_checker, children)
        self.on_pressed = on_pressed

    def ui_data(self, _id):
        return '<span><ons-button id="{}" class="script_control" onclick="script.script_interact_button(event)">Go</ons-button>{}</span>'.format(_id, self.title)

    def set_on_pressed(self, func: callable):
        self.on_pressed = func


    def handle_interaction(self, data):
        if self.on_pressed:
            self.add_instruction(self.on_pressed)




