import json

from app.script_ui import controls


class TrendResultsGroup(controls.Group):
    def __init__(self, on_copy:callable, on_max:callable, on_min: callable, **kwargs):
        super().__init__(**kwargs)
        self.trend_data: dict = None
        self.capture_info: dict = None
        self.on_copy = on_copy
        self.on_max = on_max
        self.on_min = on_min

    def format_data_row(self, data_row: list):
        new_data_row = []
        current = None
        for d in data_row:
            if d != current:
                current = d
                new_data_row.append(d)
        return " ".join([str(x) for x in new_data_row])

    def generate(self):
        start = self.capture_info['start']
        html_list = ''
        button_index = 0
        for key in self.trend_data.keys():
            html_header_row =  '<ons-row>'
            html_header_row += '<ons-col align="center" class="col ons-col-inner"><p class="address">{:X}</p></ons-col>'.format(key+start)
            html_header_row += '<ons-col align="center" class="col ons-col-inner" width="60px">'
            html_header_row += '<ons-button id="{}_copybutton-{:03}" modifier="quiet" data-address="{}" data-function="copy" onclick="script.script_interact_button(event)"><ons-icon icon="md-copy" size="15px"></ons-icon></ons-button>'.format(self.script_ids[-1], button_index, key+start)
            html_header_row += '</ons-col>'
            html_header_row += '<ons-col align="center" class="col ons-col-inner" width="60px">'
            html_header_row += '<ons-button id="{}_minbutton-{:03}" modifier="quiet" data-address="{}" data-function="min" data-key="{}" onclick="script.script_interact_button(event)">MIN</ons-button>'.format(self.script_ids[-1], button_index, key+start, key)
            html_header_row += '</ons-col>'
            html_header_row += '<ons-col align="center" class="col ons-col-inner" width="60px">'
            html_header_row += '<ons-button id="{}_maxbutton-{:03}" modifier="quiet" data-address="{}" data-function="max" data-key="{}" onclick="script.script_interact_button(event)">MAX</ons-button>'.format(self.script_ids[-1], button_index, key+start, key)
            html_header_row += '</ons-col>'
            html_header_row += '</ons-row>'
            html_data_row = '<ons-row>{}</ons-row>'.format(self.format_data_row(self.trend_data[key]))
            html_list += '<ons-list-item>{}{}</ons-list-item>\n'.format(html_header_row, html_data_row)
            button_index += 1
        return '\n<ons-list>{}</ons-list>\n'.format(html_list)

    def handle_interaction(self, _id: str, data):
        func = data['data']['function']
        address = '{:X}'.format(data['data']['address'])
        if func == 'copy':
            self.update_queue.put({'op': "script", 'data': {'script': 'document.clipboard.copy({})'.format(json.dumps({'address': address}))}})
            if self.on_copy:
                self.on_copy(self.get_id(), _id, data)
        elif func == 'min':
            if self.on_min:
                min_data = {'address': data['data']['address'], 'key': data['data']['key']}
                self.on_min(self.get_id(), _id, min_data)
        elif func == 'max':
            if self.on_max:
                min_data = {'address': data['data']['address'], 'key': data['data']['key']}
                self.on_max(self.get_id(), _id, min_data)


    def set_trend_data(self, trend_data: dict, capture_info: dict):
        self.trend_data = trend_data
        self.capture_info = capture_info
        data = self.generate()
        self.inner(data)
