from app.script_ui.button import Button
from app.script_ui.input import Input

class InputButton(Button):

    def __init__(self, name: str, title: str, on_pressed: callable = None, on_text_changed=None, enable_checker: callable = None, children=None, default_text="", validator=None):
        self.inp = Input(name+"_INPUT", title, on_changed=on_text_changed, enable_checker=enable_checker, validator=validator, change_on_focus=False, default_text=default_text)
        if children:
            children.append(self.inp)
        else:
            children = [self.inp]
        super().__init__(name, "", on_pressed, enable_checker, children)

    def get_input_control(self):
        return self.inp





