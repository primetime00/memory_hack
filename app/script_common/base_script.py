import logging
from typing import List
from app.helpers.memory import Memory
from app.script_ui.list import ListUI
from app.script_ui._base import BaseUI
from app.script_common.aob import AOB

class BaseScript:
    def __init__(self):
        self.title = ""
        self.list_ui: ListUI = ListUI()
        self.build_ui()

    aobs = set()

    def on_load(self):
        pass

    def on_unload(self):
        print('unload stub')

    def add_ui_element(self, element: BaseUI):
        self.list_ui.add(element)
        element.update_status()

    def get_ui(self):
        ui = "<h2>{}</h2>".format(self.get_name())
        return ui+self.list_ui.present()

    def get_ui_status(self):
        controls = {'enabled': [], 'disabled': []}
        for item in self.list_ui.ui_list:
            if item.is_enabled():
                controls['enabled'].append(item.get_id())
            else:
                controls['disabled'].append(item.get_id())
        return controls

    def build_ui(self):
        pass

    def add_aob(self, aob: AOB):
        self.aobs.add(aob)

    def get_app(self):
        return []

    def get_name(self):
        return 'default'

    def get_speed(self):
        return 1

    def handle_interaction(self, id, data):
        item = self.list_ui.get_id(id)
        item.base_handle_interaction(data)

    def on_aob_lost(self, aob: AOB):
        for item in self.list_ui.ui_list:
            item.update_status()

    def on_aob_found(self, aob: AOB):
        for item in self.list_ui.ui_list:
            item.update_status()

    def process(self, memory: Memory):
        for aob in self.aobs:
            if not aob.is_found():
                self.find_address(memory, aob)
            else:
                self.compare_aob(memory, aob)
        for item in self.list_ui.ui_list:
            if item.is_enabled():
                item.process(memory)


    def find_address(self, memory, aob: AOB):
        addrs = memory.search_aob(aob.get_aob_string())
        if len(addrs) == 0:
            logging.warning('Cannot find aob {} [{}]'.format(aob.get_name(), aob.get_aob_string()))
            aob.clear_bases()
        elif len(addrs) > 1:
            logging.warning('aob has multiple matches [{}] {} [{}]'.format(len(addrs), aob.get_name(), aob.get_aob_string()))
        aob.set_bases(addrs)
        self.on_aob_found(aob)

    def compare_aob(self, memory, aob:AOB):
        bases = aob.get_bases()
        bases_length = len(bases)
        for i in range(bases_length - 1, -1, -1):
            base = bases[i]
            res, old, new = memory.compare(base, aob.get_aob_string())
            if not res:
                bases.pop()
                logging.warning('aob {} does not match!\n{}\n{}'.format(aob.get_name(), old, new))
        if len(bases) == 0:
            logging.info('aob {} has no matches anymore'.format(aob.get_name()))
            self.on_aob_lost(aob)