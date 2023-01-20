from ..button import Button


class TrendButton(Button):

    def __init__(self, on_click: callable, quiet: bool = True, **kwargs):
        super().__init__("", on_click, quiet, **kwargs)
        size = kwargs.get('size', 20)
        self.quiet = True
        self.direction = 'up' #up, incline, flat, decline, down
        self.direction_map = {'up': {'icon': 'md-long-arrow-up', 'rotate': '0'},
                              'incline': {'icon': 'md-arrow-right-top', 'rotate': '0'},
                              'flat': {'icon': 'md-long-arrow-right', 'rotate': '0'},
                              'decline': {'icon': 'md-arrow-left-bottom', 'rotate': '270'},
                              'down': {'icon': 'md-long-arrow-down', 'rotate': '0'}}
        self._button_id = ''
        self.direction_list = ['up', 'incline', 'flat', 'decline', 'down']
        self.direction_index = 0

    def get_icon_html(self):
        return '<ons-icon icon="{}" rotate="{}"/>'.format(self.direction_map[self.direction]['icon'], self.direction_map[self.direction]['rotate'])

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        return '<ons-button id="{}" {} onclick="script.script_interact_button(event)">{}</ons-button>'.format(self.script_ids[-1], 'modifier="quiet"' if self.quiet else '', self.get_icon_html())

    def _on_pressed(self):
        self.direction_index += 1
        self.direction_index %= len(self.direction_list)
        self.direction = self.direction_list[self.direction_index]
        self.inner(self.get_icon_html())


    def handle_interaction(self, _id: str, data):
        self._on_pressed()
        del data['data']
        data['direction'] = self.direction
        return super().handle_interaction(_id, data)

    def get_direction(self):
        return self.direction

    def set_direction(self, direction: str):
        if direction.casefold() not in self.direction_list:
            return
        self.direction = direction.lower()
        self.direction_index = self.direction_list.index(self.direction)
        self.inner(self.get_icon_html())

    def on_reload(self):
        self.set_direction(self.direction)
        super().on_reload()










