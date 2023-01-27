from typing import List

from .element import Element


class Group(Element):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.group_items: List[Element] = []

    def children(self):
        return self.group_items

    def build(self, id_map: {}):
        element_data = []
        for item_index in range(0, len(self.children())):
            item: Element = self.children()[item_index]
            item.add_script_id(item_index, parent=self.script_ids[-1])
            element_data.append(item.perform_build(id_map))

        id_map[self.script_ids[-1]] = self
        data = '<div id="{}" style="{}">'.format(self.script_ids[-1], self.style)
        for index in range(0, len(element_data)):
            element_html = element_data[index]
            data += '\n{}'.format(element_html)
        data += '</div>'
        return data

    def process(self):
        for item in self.children():
            item.perform_process()

    def handle_interaction(self, _id: str, data):
        element_name = self.id_map[_id].get_id()
        res = self.on_interaction(element_name, _id, data)
        super().handle_interaction(_id, data)
        return res

    def on_interaction(self, name: str, ele_id: str, data):
        return True








