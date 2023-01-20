from .base_control import BaseControl

class Toggle(BaseControl):

    def __init__(self, on_toggle: callable, **kwargs):
        super().__init__(**kwargs)
        self.on = False
        if 'checked' in kwargs:
            self.on = kwargs['checked']
        self.on_toggle = on_toggle

    def set_on_toggle(self, on_toggle:callable):
        self.on_toggle = on_toggle

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        return '<ons-switch id="{}" onchange="script.script_interact_toggle(event)" {}></ons-switch>'.format(self.script_ids[-1], ("checked" if self.on else ""))

    def handle_interaction(self, _id: str, data):
        self.on = data['checked']
        if self.on_toggle:
            self.on_toggle(self.get_id(), _id, data)
        return super().handle_interaction(_id, data)

    def is_checked(self):
        return self.on

    def check(self, id_index=-1):
        self.on = True
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "prop", 'data': {'name': 'checked', 'value': True, 'id': x}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "prop", 'data': {'name': 'checked', 'value': True, 'id': '{}'.format(self.script_ids[id_index])}})

    def uncheck(self, id_index=-1):
        self.on = False
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "prop", 'data': {'name': 'checked', 'value': False, 'id': x}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "prop", 'data': {'name': 'checked', 'value': False, 'id': '{}'.format(self.script_ids[id_index])}})

    def on_reload(self):
        if self.on:
            self.check()
        else:
            self.uncheck()
        super().on_reload()








