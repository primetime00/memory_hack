import logging

import mem_edit

from app.script_common.aob import AOB
from app.script_common.utilities import ScriptUtilities
from app.script_ui._base import BaseUI
from app.script_ui.list import ListUI


class BaseScript:
    def __init__(self):
        self.memory: mem_edit.Process = None
        self.utilities = ScriptUtilities()
        self.process_name:str = ""
        self.list_ui: ListUI = ListUI()
        self.build_ui()

    aobs = set()

    def on_load(self):
        self.aobs.clear()
        pass

    def on_unload(self):
        self.aobs.clear()

    def set_memory(self, mem: mem_edit.Process):
        self.memory = mem

    def get_memory(self) -> mem_edit.Process:
        return self.memory

    def set_process(self, proc: str):
        self.process_name = proc

    def get_process(self) -> str:
        return self.process_name

    def add_ui_element(self, element: BaseUI):
        self.list_ui.add(element)
        element.update_status()

    def get_ui(self):
        ui = "<h2>{}</h2>".format(self.get_name())
        ui += "<h3>{}</h3>".format(self.get_process())
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

    def process_lost(self):
        self.aobs.clear()

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

    def _on_aob_lost(self, aob: AOB):
        self.on_aob_lost(aob)
        for item in self.list_ui.ui_list:
            item.update_status()

    def on_aob_lost(self, aob: AOB):
        pass

    def _on_aob_found(self, aob: AOB):
        self.on_aob_found(aob)
        for item in self.list_ui.ui_list:
            item.update_status()

    def on_aob_found(self, aob: AOB):
        pass


    def search(self):
        for aob in self.aobs:
            if not aob.is_found():
                self.find_address(aob)
            else:
                self.compare_aob(aob)

    def process(self):
        for item in self.list_ui.ui_list:
            if item.is_enabled():
                item.process()


    def find_address(self, aob: AOB):
        addrs = self.utilities.search_aob_all_memory(self.memory, aob)
        if len(addrs) == 0:
            if aob.will_warn():
                logging.warning('Cannot find aob {} [{}]'.format(aob.get_name(), aob.get_aob_string()))
            aob.clear_bases()
        elif len(addrs) > 1:
            logging.warning('aob has multiple matches [{}] {} [{}]'.format(len(addrs), aob.get_name(), aob.get_aob_string()))
        aob.set_bases([x['address'] for x in addrs])
        self._on_aob_found(aob)

    def compare_aob(self, aob:AOB):
        bases = aob.get_bases()
        bases_length = len(bases)
        for i in range(bases_length - 1, -1, -1):
            base = bases[i]
            res, old, new = self.utilities.compare_aob(base, aob)
            if not res:
                bases.pop(i)
                logging.warning('aob {} does not match!\n{}\n{}'.format(aob.get_name(), old, new))
        if len(bases) == 0:
            logging.info('aob {} has no matches anymore'.format(aob.get_name()))
            self._on_aob_lost(aob)
