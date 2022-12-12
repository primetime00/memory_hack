from app.script_ui.input import Input
from app.script_ui.toggle import Toggle


class InputToggle(Toggle):

    def __init__(self, name: str, title: str , on_changed: callable = None, enable_checker:callable = None, children=None, default_text="", validator=None):
        self.inp = Input(name+"_INPUT", title, on_changed=on_changed, enable_checker=enable_checker, validator=validator, change_on_focus=False, default_text=default_text)
        if children:
            children.append(self.inp)
        else:
            children = [self.inp]
        super().__init__(name, "", on_changed, enable_checker, children)

    def get_input_control(self):
        return self.inp


