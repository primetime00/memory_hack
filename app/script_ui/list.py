from typing import List

from app.helpers.exceptions import ScriptException
from app.script_ui._base import BaseUI


class ListUI:
    def __init__(self):
        self.ui_list: List[BaseUI] = []

    def add(self, item: BaseUI):
        item.id = "control_{}".format(len(self.ui_list))
        self.ui_list.append(item)

    def get_id(self, id) -> BaseUI:
        for i in self.ui_list:
            if i.id == id:
                return i
        raise ScriptException("Script id is not found.")

    def present(self):
        if self.ui_list:
            data = "<ons-list>\n"
            for item in self.ui_list:
                data += item.base_ui_data()
            data += "</ons-list>\n"
            return data
        return ""

