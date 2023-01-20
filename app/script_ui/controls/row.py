from .column import Column
from .element import Element
from typing import List


class Row(Element):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.row_items: List[Element] = []
        self.style += "min-height: 50px;"

    def children(self):
        return self.row_items

    def build(self, id_map: {}):
        element_data = []
        for item_index in range(0, len(self.children())):
            item: Element = self.children()[item_index]
            item.add_script_id(item_index, parent=self.script_ids[-1])
            element_data.append(item.perform_build(id_map))

        id_map[self.script_ids[-1]] = self
        data = '<ons-row id="{}" vertical-align="center" style="{}">'.format(self.script_ids[-1], self.style)
        for element_html in element_data:
            data += '{}'.format(element_html)
        data += '</ons-row>'
        return data

    def process(self):
        for item in self.children():
            item.perform_process()

    def add_elements(self, elements: List['Element']):
        for ele in elements:
            col = self.add_element(Column())
            col.add_element(ele)
        return self











