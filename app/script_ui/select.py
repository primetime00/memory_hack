from app.script_ui._base import BaseUI


class Select(BaseUI):

    def __init__(self, name: str, title: str , on_changed: callable = None, enable_checker:callable = None, children=None, values=None):
        super().__init__(name, title, enable_checker, children)
        self.values = [] if not values else values
        self.selection = None if not self.values else self.values[0][0]
        self.on_changed = on_changed

    def ui_data(self, _id):
        if self.values:
            data = ""
            for _val, _txt in self.values:
                data += '<option value="{}">{}</option>\n'.format(_val, _txt)
            return '<span><select id="{}" class="select-input select-input--material" onchange="script.script_interact_select(event)">{}</select> {}</span>'.format(_id, data, self.title)
        else:
            return '<span><select id="{}" class="select-input select-input--material" onchange="script.script_interact_select(event)"></select> {}</span>'.format(_id, self.title)

    def set_on_changed(self, func: callable):
        self.on_changed = func

    def handle_interaction(self, data):
        self.selection = data['value']
        if self.on_changed:
            self.add_instruction(self.on_changed, (self.selection,))

    def set_values(self, vals):
        self.values = vals
        self.selection = self.values[0][0]
        self.create_html()

    def set_value(self, val):
        self.selection = val
        if self.selection not in [v[0] for v in self.values]:
            self.values.insert(0, self.selection)
            self.create_html()
        self.update_queue.put({'op': "value", 'data': {'value': self.selection}})

    def create_html(self):
        data = ""
        for v, t in self.values:
            data += '<option value="{}">{}</option>\n'.format(v, t)
        self.inner(data)

    def get_selection(self):
        return self.selection
