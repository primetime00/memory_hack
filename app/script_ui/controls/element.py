from queue import Queue
from typing import List, Dict

from .build import Build


class Element(Build):
    def __init__(self, **kwargs):
        super().__init__()
        if 'id' not in kwargs:
            self.id = self.__class__.__name__.upper()+'_'+str(id(self))
        else:
            _id = str(kwargs['id'])
            if len(_id.strip()) == 0:
                self.id = self.__class__.__name__.upper() + '_' + str(id(self))
            else:
                self.id = _id
        self.parent = None
        self.script_ids = []
        self.on_process = None
        self.on_process_args = None

        self.interact_queue = Queue()
        self.update_queue = Queue()

        self.updated = False
        self.return_data = None

        self.enabled = True
        self.hidden = False

        self.id_map: Dict[str, Element] = {}
        self.element_map: Dict[str, Element] = {}
        self.style: str = kwargs.get('style', '')
        self.keys = kwargs

        self.data_map: dict = {}

    def children(self) -> List['Element']:
        return []

    def add_element(self, ele: 'Element') -> 'Element':
        self.children().append(ele)
        ele.parent = self
        return ele

    def add_elements(self, elements: List['Element']):
        for ele in elements:
            self.add_element(ele)
        return self


    def get_id(self):
        return self.id

    def get_script_head(self):
        return self.__class__.__name__.lower()

    def add_script_id(self, _id: int, parent: str = None):
        if parent is None:
            self.script_ids.append('{}-{:03}'.format(self.get_script_head(), _id))
        else:
            self.script_ids.append('{}_{}-{:03}'.format(parent, self.get_script_head(), _id))


    def get_script_ids(self):
        return self.script_ids

    def get_parent(self):
        return self.parent

    def set_on_process(self, func: callable, *args):
        self.on_process = func
        self.on_process_args = args

    def get_return_data(self):
        return self.return_data

    def add_instruction(self, function, args=()):
        self.interact_queue.put((function, args))

    def base_handle_interaction(self, _id, data):
        self.handle_interaction(_id, data)

    def handle_interaction(self, _id:str, data):
        return True

    def perform_process(self):
        while not self.interact_queue.empty():
            func, args = self.interact_queue.get()
            func(self, *args)
        self.process()
        if self.on_process:
            self.on_process(self, self.on_process_args)

    def process(self):
        pass

    def get_render_updates(self):
        update_list = []
        while not self.update_queue.empty():
            update_list.append(self.update_queue.get())
        return update_list

    def hide(self, id_index: int = -1):
        self.hidden = True
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "script", 'data': {'id': x, 'script': '$("#{}").hide();'.format(x)}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "script", 'data': {'script': '$("#{}").hide();'.format(self.script_ids[id_index]), 'id': '{}'.format(self.script_ids[id_index])}})

    def show(self, id_index: int = -1):
        self.hidden = False
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "script", 'data': {'script': '$("#{}").show();'.format(x)}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "script", 'data': {'script': '$("#{}").show();'.format(self.script_ids[id_index])}})

    def disable(self, id_index: int = -1):
        self.enabled = False
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "prop", 'data': {'name': 'disabled', 'value': True, 'id': x}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "prop", 'data': {'name': 'disabled', 'value': True, 'id': '{}'.format(self.script_ids[id_index])}})

    def js(self, script: str, id_index: int = -1):
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "script", 'data': {'script': script, 'id': x}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "script", 'data': {'script': script, 'id': '{}'.format(self.script_ids[id_index])}})

    def add_style(self, style: str):
        self.js("const style = document.createElement('style'); style.textContent = '{}'; document.head.append(style);".format(style))

    def enable(self, id_index: int = -1):
        self.enabled = True
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "prop", 'data': {'name': 'disabled', 'value': False, 'id': x}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "prop", 'data': {'name': 'disabled', 'value': False, 'id': '{}'.format(self.script_ids[id_index])}})

    def inner(self, html: str, id_index: int = -1):
        if id_index < 0 or id_index >= len(self.script_ids):
            [self.update_queue.put({'op': "inner-html", 'data': {'html': html, 'id': x}}) for x in self.script_ids]
        else:
            self.update_queue.put({'op': "inner-html", 'data': {'html': html, 'id': '{}'.format(self.script_ids[id_index])}})

    def is_hidden(self):
        return self.hidden

    def is_enabled(self):
        return self.enabled

    def get_element(self, name: str):
        if name in self.element_map:
            return self.element_map[name]
        return None

    def get_data(self, key: str):
        return self.data_map.get(key, None)

    def put_data(self, key: str, data):
        self.data_map[key] = data


    def on_ready(self):
        pass

    def on_reload(self):
        if self.hidden:
            self.hide()
        else:
            self.show()
        if self.enabled:
            self.enable()
        else:
            self.disable()


