from typing import List
from typing import Union

from .build import Build
from .element import Element
from .row import Row


class Page(Element):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elements = []
        self.header: str = None

    def children(self):
        return self.elements

    def build(self, id_map):
        element_data = []
        for element_index in range(0, len(self.children())):
            ele: Union[Element, Build] = self.children()[element_index]
            ele.add_script_id(element_index, parent=self.script_ids[-1])
            element_data.append(ele.perform_build(id_map))
        id_map[self.script_ids[-1]] = self
        data = ''
        if self.header:
            data += '<ons-list-header id="header{}">{}</ons-list-header>'.format(self.script_ids[-1], self.header)
        data += '<ons-list-item id="{}" style="{}" modifier="longdivider">'.format(self.script_ids[-1], self.style)
        data += "\n\t".join(element_data)
        data += '</ons-list-item>'
        return data

    def process(self):
        for ele in self.children():
            ele.perform_process()

    def add_elements(self, elements: List[Element], **kwargs):
        if not elements:
            return self
        if 'id' not in kwargs:
            row = self.add_element(Row())
        else:
            row = self.add_element(Row(id=kwargs.get('id')))
        row.add_elements(elements)
        return self

    def set_header(self, header: str):
        self.header = header

    def hide(self, id_index: int = -1):
        super().hide(id_index)
        if self.header:
            if id_index < 0 or id_index >= len(self.script_ids):
                [self.update_queue.put({'op': "script", 'data': {'id': x, 'script': '$("#header{}").hide();'.format(x)}}) for x in self.script_ids]
            else:
                self.update_queue.put({'op': "script", 'data': {'script': '$("#header{}").hide();'.format(self.script_ids[id_index]), 'id': '{}'.format(self.script_ids[id_index])}})

    def show(self, id_index: int = -1):
        super().show(id_index)
        if self.header:
            if id_index < 0 or id_index >= len(self.script_ids):
                [self.update_queue.put({'op': "script", 'data': {'id': x, 'script': '$("#header{}").show();'.format(x)}}) for x in self.script_ids]
            else:
                self.update_queue.put({'op': "script", 'data': {'script': '$("#header{}").show();'.format(self.script_ids[id_index]), 'id': '{}'.format(self.script_ids[id_index])}})













