from app.script_ui import controls

class TrendRow(controls.Row):
    def __init__(self, on_clicked: callable, **kwargs):
        super().__init__(**kwargs)
        self.max_trends = 8
        self.trend_count = 1
        self.build_ui()
        self.trend_list = ['up'] * self.max_trends
        self.on_clicked = on_clicked


    def build_ui(self):
        row_1: controls.Row = self.add_element(controls.Row())
        row_2: controls.Row = self.add_element(controls.Row())

        for i in range(0, self.max_trends):
            row_1.add_element(controls.advanced.TrendButton(on_click=self.on_click, id="_TREND_BUTTON_{}".format(i)))

        row_2.add_elements([
            controls.Button("Add", self.on_add, False, id="_TREND_ROW_ADD_BUTTON"),
            controls.Button("Remove", self.on_remove, False, id="_TREND_ROW_REMOVE_BUTTON")
        ])

    def on_ready(self):
        for i in range(1, self.max_trends):
            self.get_element("_TREND_BUTTON_{}".format(i)).hide()
        self.get_element("_TREND_ROW_REMOVE_BUTTON").disable()

    def on_click(self, name:str, ele, data):
        index = int(name.split('_')[-1])
        self.trend_list[index] = data['direction']
        if self.on_clicked:
            self.on_clicked(name, ele, data)

    def on_add(self, name, ele, data):
        if self.trend_count > self.max_trends:
            self.trend_count = self.max_trends
            return
        self.trend_count += 1
        tb: controls.advanced.UpDownButton = self.get_element("_TREND_BUTTON_{}".format(self.trend_count - 1))
        tb.show()
        self.get_element("_TREND_ROW_REMOVE_BUTTON").enable()
        if self.trend_count >= self.max_trends:
            self.get_element("_TREND_ROW_ADD_BUTTON").disable()
        if self.on_clicked:
            self.on_clicked(name, ele, data)


    def on_remove(self, name, ele, data):
        if self.trend_count < 2:
            self.trend_count = 1
            return
        self.trend_count -= 1
        tb: controls.advanced.UpDownButton = self.get_element("_TREND_BUTTON_{}".format(self.trend_count))
        tb.hide()
        tb.set_direction('')
        self.trend_list[self.trend_count] = ''
        self.get_element("_TREND_ROW_ADD_BUTTON").enable()
        if self.trend_count == 1:
            self.get_element("_TREND_ROW_REMOVE_BUTTON").disable()
        if self.on_clicked:
            self.on_clicked(name, ele, data)


    def get_trend_list(self):
        return self.trend_list[0: self.trend_count]
