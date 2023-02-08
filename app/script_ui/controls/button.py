from .base_control import BaseControl

class Button(BaseControl):

    def __init__(self, text: str, on_click: callable, quiet: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.quiet = quiet
        self.on_click = on_click
        self.custom_data = kwargs.get('custom_data', [])
        self.pressed = False

    def set_on_click(self, on_click:callable):
        self.on_click = on_click

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        data = '<ons-button id="{}" {} onclick="script.script_interact_button(event)">{}</ons-button>'.format(self.script_ids[-1], 'modifier="quiet"' if self.quiet else '', self.text)
        if self.custom_data:
            data = data[0:data.index('id=')] + 'data-{}="{}"'.format(self.custom_data[0], self.custom_data[1]) + data[data.index('id='):]
        return data

    def pop_pressed(self):
        pressed = self.pressed
        self.pressed = False
        return pressed

    def was_pressed(self):
        return self.pressed

    def handle_interaction(self, _id: str, data):
        self.pressed = True
        if self.on_click:
            self.on_click(self.get_id(), _id, data)
        return super().handle_interaction(_id, data)

    def process(self):
        super().process()
        self.pop_pressed()










