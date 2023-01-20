from .base_control import BaseControl

class Select(BaseControl):

    def __init__(self, values: list, on_change: callable, **kwargs): #values should a (value, text) tuple
        super().__init__(**kwargs)
        self.values = [] if not values else values
        self.selection = None if not self.values else self.values[0][0]
        self.on_change = on_change
        self.default_selection = kwargs.get('select_index', 0)

    def set_on_change(self, on_change:callable):
        self.on_change = on_change

    def on_ready(self):
        if self.default_selection > 0:
            self.set_select_index(self.default_selection)

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        data = ""
        if self.values:
            for _val, _txt in self.values:
                data += '<option value="{}">{}</option>\n'.format(_val, _txt)
        cb = 'script.script_interact_select(event)'
        res = '<select id="{}" class="select-input select-input--material" onchange="{}">{}</select>'.format(self.script_ids[-1], cb, data)
        return res

    def handle_interaction(self, _id: str, data):
        self.selection = data['value']
        if self.on_change:
            self.on_change(self.get_id(), _id, data)
        return super().handle_interaction(_id, data)

    def _set_values(self, vals):
        data = ""
        for v, t in vals:
            data += '<option value="{}">{}</option>\n'.format(v, t)
        self.inner(data)

    def set_values(self, vals):
        self.values = vals
        self.selection = self.values[0][0]
        self._set_values(vals)

    def set_value(self, val):
        self.selection = val
        if self.selection not in [v[0] for v in self.values]:
            self.values.insert(0, self.selection)
            self._set_values(self.values)
        [self.update_queue.put({'op': "value", 'data': {'value': self.selection, 'id': '{}'.format(x)}}) for x in self.script_ids]

    def get_selection(self):
        return self.selection

    def set_select_index(self, index):
        if 0 <= index < len(self.values):
            self.selection = self.values[index][0]
            [self.update_queue.put({'op': "value", 'data': {'value': self.selection, 'id': '{}'.format(x)}}) for x in self.script_ids]

    def on_reload(self):
        cv = self.selection
        if cv and self.values:
            self.set_values(self.values)
            self.set_value(cv)
        super().on_reload()






