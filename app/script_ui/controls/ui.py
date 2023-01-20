from app.helpers.exceptions import ScriptException
from .element import Element
from .page import Page


class UI(Element):

    def __init__(self, **kwargs):
        super().__init__(id='ui_root')
        self.pages: list[Page] = []
        self.script_ids.append('ui_root')
        self.html:str = None
        self.title = kwargs.get('title', 'Untitled')
        self.author = kwargs.get('author', 'Unknown')
        self.version = kwargs.get('version', '0.0.0')

    def add_page(self, pg: Page) -> Page:
        self.pages.append(pg)
        pg.parent = self
        return pg

    def add_element(self, ele: Element) -> Element:
        raise ScriptException('Cannot add base elements.  Only pages')

    def children(self):
        return self.pages

    def process(self):
        if not self.is_built():
            self.id_map.clear()
            self.perform_build(self.id_map)
        for page in self.children():
            page.perform_process()

    def build(self, _):
        page_data = []
        for page_index in range(0, len(self.children())):
            page: Element = self.children()[page_index]
            page.add_script_id(page_index)
            page_data.append(page.perform_build(self.id_map))
        self.id_map[self.script_ids[-1]] = self
        self.generate_element_map()
        data = '<ons-row vertical-align="center" style="max-height: 40px;"><ons-col><h2>{}</h2></ons-col><ons-col width="160px"><p style="font-size: 9pt; text-align: right;">{}</p></ons-col></ons-row>\n\n'.format(self.title, self.version)
        data += '<ons-row vertical-align="center"><p style="font-size: 9pt;">{}</p></ons-row>\n\n'.format(self.author)
        data += '<ons-list id="{}">'.format(self.script_ids[-1])
        data += "\n\t".join(page_data)
        data += '</ons-list>'
        self.html = data
        return data

    def generate_element_map(self):
        for proc in self.id_map.values():
            self.element_map[proc.get_id()] = proc
        for proc in self.id_map.values():
            proc.id_map = self.id_map
            proc.element_map = self.element_map

    def generate_data_map(self, data_map: dict):
        for proc in self.id_map.values():
            proc.data_map = data_map



    def handle_interaction(self, _id:str, data):
        current_id = _id
        original_id = _id
        while current_id not in self.id_map:
            try:
                current_id = current_id[0:current_id.rindex('_')]
            except ValueError:
                return
        _id = current_id
        ele: Element = self.id_map[_id]
        bubble = ele.handle_interaction(original_id, data)
        current_id = _id
        while bubble:
            try:
                current_id = current_id[0:current_id.rindex('_')]
                if current_id not in self.id_map:
                    continue
                bubble = self.id_map[current_id].handle_interaction(_id, data)
            except ValueError:
                break
        return bubble

    def retrieve_updates(self):
        updates = self.get_render_updates()
        for script_id, proc in self.id_map.items():
            updates.extend(proc.get_render_updates())
        return updates


    def get_html(self):
        return self.html

    def ready(self):
        for proc in self.id_map.values():
            proc.on_ready()

    def set_page_header(self, pg: Page, header: str):
        pg.set_header(header)

    def on_reload(self):
        for proc in self.id_map.values():
            if proc != self:
                proc.on_reload()







