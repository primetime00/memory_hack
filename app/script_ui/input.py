from app.script_ui._base import BaseUI
class Input(BaseUI):

    def __init__(self, name: str, title: str, on_changed: callable = None, enable_checker:callable = None, children=None, default_text="", change_on_focus=True, validator=None):
        super().__init__(name, title, enable_checker, children)
        self.text = default_text
        self.on_changed = on_changed
        self.change_on_focus = change_on_focus
        self.validator = validator

    def ui_data(self, _id):
        if not self.change_on_focus:
            return '<span><ons-input id="{}" modifier="underbar" placeholder="{}" oninput="script.script_interact_value(event)" float></ons-input> {}</span>'.format(_id, self.text, self.title)
        else:
            return '<span><ons-input id="{}" modifier="underbar" placeholder="{}" onchange="script.script_interact_value(event)" float></ons-input> {}</span>'.format(_id, self.text, self.title)

    def set_on_changed(self, func: callable):
        self.on_changed = func

    def set_validator(self, func: callable):
        self.validator = func

    def handle_interaction(self, data):
        text = data['value']
        if self.validator:
            if self.validator(text):
                self.text = text
                if self.on_changed:
                    self.add_instruction(self.on_changed, (text, ))
            else:
                self.set_text(self.text)
        else:
            self.text = text
            if self.on_changed:
                self.add_instruction(self.on_changed, (text, ))
    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self.update_queue.put({'op': "value", 'data': {'value': text}})

