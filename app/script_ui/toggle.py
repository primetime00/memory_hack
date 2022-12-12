from app.script_ui._base import BaseUI

class Toggle(BaseUI):

    def __init__(self, name: str, title: str , on_changed: callable = None, enable_checker:callable = None, children=None):
        super().__init__(name, title, enable_checker, children)
        self.on = False
        self.on_changed = on_changed

    def ui_data(self, _id):
        return '<ons-switch id="{}" class="script_control" onchange="script.script_interact_toggle(event)" {}></ons-switch>{}'.format(self.id, ("checked" if self.on else ""), self.title)

    def set_on_changed(self, func: callable):
        self.on_changed = func
    def check(self):
        self.update_queue.put({'op': "prop", 'data': {'name': 'checked', 'value': True}})
        self.on = True
        if self.on_changed:
            self.on_changed(self, True)

    def uncheck(self):
        self.update_queue.put({'op': "prop", 'data': {'name': 'checked', 'value': False}})
        self.on = False
        if self.on_changed:
            self.on_changed(self, False)

    def handle_interaction(self, data):
        self.on = data['checked']
        if self.on_changed:
            self.on_changed(self, self.on)

    def is_checked(self):
        return self.on



