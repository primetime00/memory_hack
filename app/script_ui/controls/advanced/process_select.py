from app.helpers.data_store import DataStore
from ..button import Button
from ..column import Column
from ..group import Group
from ..row import Row
from ..select import Select
from ..text import Text


class ProcessSelect(Group):
    def __init__(self, on_process_selected: callable, **kwargs):
        super().__init__(**kwargs)
        self.on_process_selected = on_process_selected
        row1 = self.add_element(Row())
        col1 = row1.add_element(Column(width="120px"))
        col2 = row1.add_element(Column())
        col1.add_element(Text("Select Process:"))
        col2.add_element(Select([], self.on_process_select_changed, id="PROCESS_SELECT_CONTROL"))
        row2 = self.add_element(Row())
        row2.add_element(Button("Refresh", self.on_refresh_pressed, id="REFRESH_PROCESS_LIST_BUTTON"))
        self.style = 'margin: 0px 0px;'

    def build(self, id_map: {}):
        return super().build(id_map)

    def on_ready(self):
        self.refresh()

    def on_reload(self):
        select: Select = self.get_element("PROCESS_SELECT_CONTROL")
        if select.get_selection() != '_null':
            self.get_element("REFRESH_PROCESS_LIST_BUTTON").disable()
        else:
            self.get_element("REFRESH_PROCESS_LIST_BUTTON").enable()
        super().on_reload()

    def refresh(self):
        select: Select = self.get_element("PROCESS_SELECT_CONTROL")
        procs = [(x, x) for x in DataStore().get_service('process').get_process_list()]
        procs.insert(0, ('_null', ''))
        select.set_values(procs)

    def on_process_select_changed(self, name, ele_id, data):
        select: Select = self.get_element("PROCESS_SELECT_CONTROL")
        value = data['value']
        DataStore().get_service('script').set_app(select.get_selection())
        if value != '_null':
            self.get_element("REFRESH_PROCESS_LIST_BUTTON").disable()
            self.on_process_selected(value)
        else:
            self.get_element("REFRESH_PROCESS_LIST_BUTTON").enable()
            self.on_process_selected(None)

    def on_refresh_pressed(self, name, ele_id, data):
        self.refresh()





