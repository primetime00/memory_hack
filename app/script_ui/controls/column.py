from .element import Element


class Column(Element):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.column_items: list[Element] = []
        self.width: str = kwargs.get('width', '')

    def children(self):
        return self.column_items

    def build(self, id_map: {}):
        element_data = []
        for item_index in range(0, len(self.children())):
            item: Element = self.children()[item_index]
            item.add_script_id(item_index, parent=self.script_ids[-1])
            element_data.append(item.perform_build(id_map))

        id_map[self.script_ids[-1]] = self
        if self.width:
            data = '<ons-col id="{}" width="{}" align="center" class="col ons-col-inner" style="{}">'.format(self.script_ids[-1], self.width, self.style)
        else:
            data = '<ons-col id="{}" align="center" class="col ons-col-inner" style="{}">'.format(self.script_ids[-1], self.style)
        for element_html in element_data:
            data += '{}'.format(element_html)
        data += '</ons-col>'
        return data

    def process(self):
        for item in self.children():
            item.perform_process()

    def add_element(self, ele: 'Element') -> 'Element':
        if 'width' in ele.keys:
            self.width = ele.keys['width']
        if 'align_text' in ele.keys:
            self.style += ' text-align: {}; '.format(ele.keys['align_text'])

        return super().add_element(ele)











