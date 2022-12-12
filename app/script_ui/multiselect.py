from app.script_ui.select import Select


class MultiSelect(Select):

    def __init__(self, name: str, title: str, on_changed: callable = None, enable_checker: callable = None, children=None, values=None):
        super().__init__(name, title, on_changed, enable_checker, children, values)

    def ui_data(self, _id):
        if self.values:
            data = ""
            for _val, _txt in self.values:
                data += '<option value="{}">{}</option>\n'.format(_val, _txt)
            return '<span><select id="{}" class="select-input select-input--material" multiple onchange="script.script_interact_multi_select(event)">{}</select> {}</span>'.format(_id, data, self.title)
        else:
            return '<span><select id="{}" class="select-input select-input--material" multiple onchange="script.script_interact_multi_select(event)"></select> {}</span>'.format(_id, self.title)

