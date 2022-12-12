from typing import List

from app.helpers.exceptions import ScriptException
from app.script_ui._base import BaseUI


class ListUI:
    def __init__(self):
        self.ui_list: List[BaseUI] = []
        self.id_map = {}
        self.name_map = {}

    def add(self, item: BaseUI):
        self.set_ids(item)
        self.ui_list.append(item)
        self._add_name_to_map(item)

    def  _add_name_to_map(self, item: BaseUI):
        if item.children:
            for c in item.children:
                self._add_name_to_map(c)
            self.name_map[item.get_name()] = item
        else:
            self.name_map[item.get_name()] = item

    def set_ids(self, item:BaseUI, _uid=0):
        if _uid == 0:
            item.id = "control_{}".format(len(self.ui_list))
        else:
            item.id = "control_child_{}_{}".format(_uid, len(self.ui_list))
        self.id_map[item.id] = item
        if item.children:
            for c in item.children:
                self.set_ids(c, _uid+1)


    def get_id(self, id) -> BaseUI:
        if id not in self.id_map:
            raise ScriptException("Script id is not found.")
        return self.id_map[id]

    def get_by_name(self, name: str):
        if name in self.name_map:
            return self.name_map[name]
        return None

    def present(self):
        if self.ui_list:
            data = "<ons-list>\n"
            for item in self.ui_list:
                data += item.base_ui_data()
            data += "</ons-list>\n"
            return data
        return ""

