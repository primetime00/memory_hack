from ..button import Button


class UpDownButton(Button):

    def __init__(self, on_click: callable, quiet: bool = True, **kwargs):
        super().__init__("", on_click, quiet, **kwargs)
        size = kwargs.get('size', 20)
        self.quiet = True
        self.direction = ''
        self._up_button_id = ''
        self._dn_button_id = ''

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        row0_id = '{}_row-{:03}'.format(self.script_ids[-1], 0)
        button0_id = '{}_button-{:03}'.format(row0_id, 0)
        row1_id = '{}_row-{:03}'.format(self.script_ids[-1], 1)
        button1_id = '{}_button-{:03}'.format(row1_id, 1)
        up_button = '<ons-button id="{}" {} data-direction="up" data-other-id="{}" onclick="script.script_interact_button(event)"><ons-icon icon="md-long-arrow-up"/></ons-button>'.format(button0_id, 'modifier="quiet"' if self.quiet else '', button1_id)
        dn_button = '<ons-button id="{}" {} data-direction="down" data-other-id="{}" onclick="script.script_interact_button(event)"><ons-icon icon="md-long-arrow-down"/></ons-button>'.format(button1_id, 'modifier="quiet"' if self.quiet else '', button0_id)
        up_row = '<ons-row id="{}">{}</ons-row>'.format(row0_id, up_button)
        dn_row = '<ons-row id="{}">{}</ons-row>'.format(row1_id, dn_button)
        self._up_button_id = button0_id
        self._dn_button_id = button1_id
        group = '<div id="{}">\n{}\n{}\n</div>'.format(self.script_ids[-1], up_row, dn_row)
        return group

    def handle_interaction(self, _id: str, data):
        direction = data['data']['direction']
        other_id = data['data']['otherId']
        if self.direction == direction:
            data['direction'] = ''
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(_id)}})
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(other_id)}})
        elif direction == 'up':
            data['direction'] = 'up'
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "");'.format(_id)}})
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(other_id)}})
        else:
            data['direction'] = 'down'
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "");'.format(_id)}})
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(other_id)}})
        del data['data']
        self.direction = data['direction']
        return super().handle_interaction(_id, data)

    def get_direction(self):
        return self.direction

    def set_direction(self, direction: str):
        if direction.casefold() not in ['up', 'down', '']:
            return
        self.direction = direction.lower()
        if self.direction == 'up':
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "");'.format(self._up_button_id)}})
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(self._dn_button_id)}})
        elif self.direction == 'down':
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "");'.format(self._dn_button_id)}})
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(self._up_button_id)}})
        else:
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(self._up_button_id)}})
            self.update_queue.put({'op': "script", 'data': {'script': '$("#"+"{}").attr("modifier", "quiet");'.format(self._dn_button_id)}})

    def on_reload(self):
        self.set_direction(self.direction)
        super().on_reload()









