from .select import Select

class MultiSelect(Select):

    def __init__(self, values: list, on_change: callable, **kwargs):
        super().__init__(values, on_change, **kwargs)
        self.selection = [] if not self.values else [self.values[0][0]]
        self.default_selection = kwargs.get('select_index', [0])

    def on_ready(self):
        if not self.default_selection or self.default_selection == [0]:
            return
        self.set_select_index(self.default_selection)

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        data = ""
        if self.values:
            for _val, _txt in self.values:
                data += '<option value="{}">{}</option>\n'.format(_val, _txt)
        cb = 'script.script_interact_multi_select(event)'
        res = '<select id="{}" class="select-input select-input--material" onchange="{}" multiple>{}</select>'.format(self.script_ids[-1], cb, data)
        return res

    def set_values(self, vals):
        self.values = vals
        self.selection = [self.values[0][0]]
        self._set_values(vals)

    def set_value(self, val):
        if not isinstance(val, list):
            val = [val]
        self.selection = val
        [self.update_queue.put({'op': "value", 'data': {'value': self.selection, 'id': '{}'.format(x)}}) for x in self.script_ids]

    def set_select_index(self, index):
        if isinstance(index, list):
            index = [index]
        self.selection = []
        for i in index:
            if 0 <= i < len(self.values):
                self.selection.append(self.values[i][0])
        [self.update_queue.put({'op': "value", 'data': {'value': self.selection, 'id': '{}'.format(x)}}) for x in self.script_ids]




