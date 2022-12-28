import ctypes
import json
import platform
import re
from pathlib import Path
from queue import Queue
from threading import Thread

from app.helpers.data_store import DataStore
from app.helpers.directory_utils import scripts_memory_directory
from app.helpers.process import get_process_map
from app.script_common import BaseScript
from app.script_ui import BaseUI, Button, Select, Input, Text
from app.search.searcher_multi import SearcherMulti


class Test(BaseScript):

    def on_load(self):
        self.put_data("SYSTEM", platform.system())

    def get_name(self):
        return "Pointer Search"

    def get_app(self):
        return []

    def build_ui(self):
        self.add_ui_element(Select("PROCS", "Process", values=[('none', "None")], on_changed=self.ctrl_changed, children=[Button("REFRESH", "Refresh", on_pressed=self.refresh_pid)]))
        self.add_ui_element(Select("FILES", "Pointer File", values=[('none', "None")], on_changed=self.ctrl_changed))
        self.add_ui_element(Input("ADDRESS", "Address", on_changed=self.ctrl_changed, change_on_focus=False, validator=self.address_validator, children=[Button("PASTE", "Paste", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Button("SEARCH", "Search", on_pressed=self.ctrl_pressed))
        self.add_ui_element(Button("STOP", "Stop", on_pressed=self.ctrl_pressed))
        self.add_ui_element(Text("RESULTS", "Results"))

        self.refresh_pid(self.get_ui_control("PROCS"))
        self.populate_files()


        [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['ADDRESS', 'FILES', 'SEARCH', 'STOP', 'RESULTS', 'PASTE']]


    def refresh_pid(self, ele: BaseUI):
        procs = [(x,x) for x in DataStore().get_service('process').get_process_list()]
        procs.insert(0, ('_null', ''))
        self.get_ui_control("PROCS").set_values(procs)

    def populate_files(self):
        f_list = [('_null', '')]
        for f in Path(scripts_memory_directory).glob("*.ptr"):
            f_list.append((str(f.name), str(f.name)))
        self.get_ui_control("FILES").set_values(f_list)

    def on_clipboard_copy(self, data):
        if 'address' in data:
            self.get_ui_control("PASTE").show()
            self.put_data("CLIPBOARD", data['address'])

    def on_clipboard_clear(self):
        self.get_ui_control("PASTE").hide()

    def ctrl_changed(self, ele: BaseUI, value):
        if ele.get_name() == 'ADDRESS' or ele.get_name() == 'OFFSET' or ele.get_name() == 'LEVELS':
            self.check_for_start()
        elif ele.get_name() == 'FILES':
            self.check_for_start()
        elif ele.get_name() == 'PROCS':
            DataStore().get_service('script').set_app(self.get_ui_control("PROCS").get_selection())
            self.put_data('APP_NAME', self.get_ui_control("PROCS").get_selection())
            if value != '_null':
                [self.get_ui_control(ctrl_name).show() for ctrl_name in ['ADDRESS', 'FILES']]
            else:
                [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['ADDRESS', 'FILES', 'SEARCH', 'STOP', 'PASTE']]

    def check_for_start(self):
        if len(self.get_ui_control("ADDRESS").get_text()) > 4 and self.get_ui_control("FILES").get_selection() != '_null':
            self.get_ui_control("SEARCH").show()
        else:
            self.get_ui_control("SEARCH").hide()

    def ctrl_pressed(self, ele: BaseUI):
        if ele.get_name() == 'SEARCH':
            self.prepare_search()
        elif ele.get_name() == 'STOP':
            self.stop_search()
        elif ele.get_name() == 'PASTE':
            self.get_ui_control("ADDRESS").set_text("{:X}".format(int(self.get_data("CLIPBOARD"))))


    def address_validator(self, txt: str):
        if re.match(r'^[0-9A-F]{0,16}$', txt.upper().strip()):
            return True
        return False

    def frame(self):
        queue: Queue = self.get_data("QUEUE")
        if queue:
            while not queue.empty():
                dt = queue.get()
                if dt['status'] == "SUCCESS":
                    self.search_complete(dt)
                elif dt == "BREAK":
                    self.search_break(dt)

    def stop_search(self):
        searcher: SearcherMulti = self.get_data('SEARCHER')
        print('cancel!')
        searcher.cancel()

    def search_break(self):
        print("search cancelled")
        self.get_ui_control("STOP").hide()
        self.get_ui_control("SEARCH").show()
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['PROCS', 'ADDRESS', 'FILES']]


    def search_complete(self, status):
        print("search complete")
        print('FOUND {} valid pointers'.format(len(status['pointers'])))
        self.get_ui_control("STOP").hide()
        self.get_ui_control("SEARCH").show()
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['PROCS', 'ADDRESS', 'FILES']]
        self.get_ui_control("RESULTS").show()
        self.get_ui_control("RESULTS").set_text(self.generate_pointer_text(status['pointers']))


    def prepare_search(self):
        address = int(self.get_ui_control("ADDRESS").get_text(), 16)
        file = self.get_ui_control("FILES").get_selection()

        self.put_data("QUEUE", Queue())

        [self.get_ui_control(ctrl_name).disable() for ctrl_name in ['PROCS', 'ADDRESS', 'FILES']]

        self.get_ui_control("SEARCH").hide()
        self.get_ui_control("RESULTS").hide()
        self.get_ui_control("STOP").show()

        search_thread = Thread(target=self.search, args=(address, file, self.get_data("QUEUE")))
        search_thread.start()

    def _find_address(self, ptr, pm):
        for process in pm:
            if process['pathname'] == ptr['path'] and process['map_index'] == ptr['node']:
                return process['start'] + ptr['base_offset']
        return None

    def search(self, find_address, file, queue):
        path = Path(scripts_memory_directory).joinpath(file)
        with path.open(mode='rt') as f:
            orig_data = json.load(f)

        data = orig_data.copy()

        pm = get_process_map(self.get_memory())
        pointers = []
        for item in data:
            new_address = self._find_address(item, pm)
            if new_address:
                new_item = item.copy()
                new_item['address'] = new_address
                pointers.append(new_item)

        valid_pointers = []
        for pointer in pointers:
            address = pointer['address']
            try:
                for offset in pointer['offsets']:
                    read = self.get_memory().read_memory(address, ctypes.c_uint64()).value
                    read = read + offset
                    address = read
                if address == find_address:
                    valid_pointers.append(pointer)
            except Exception:
                continue

        #with path.open(mode='wt') as f:
        #    json.dump(valid_pointers, f, indent=4)

        queue.put({'status': 'SUCCESS', 'pointers': valid_pointers})

    def generate_pointer_text(self, pointers):
        data = "<ons-row><strong>Valid results: {}</strong></ons-row>".format(len(pointers))
        for p in pointers:
            data += "<ons-row>"

            pt = p['path'].split('/')[-1] if self.is_linux() else p['path'].split('\\')[-1]
            data += "<ons-row>{}:{}+{:X}</ons-row>".format(pt, p['node'], p['base_offset'])
            data += "<ons-row>"
            for offset in p['offsets']:
                data += '{:X}, '.format(offset)
            data = data[0:-2]
            data += "</ons-row>"
            data += "<ons-row>"
            base_address = '{}:{}+{:X}'.format(pt, p['node'], p['base_offset'])
            copy_data = "{{'base_address': '{}', 'offsets': '{}'}}".format(base_address, ", ".join("{:X}".format(x) for x in p['offsets']))
            data += '<ons-button modifier="quiet" name="copy_button" onclick="document.clipboard.copy({})">Copy</ons-button></ons-col>'.format(copy_data)
            data += "</ons-row>"

            data += "</ons-row>"
        return data

    def is_linux(self):
        return self.get_data("SYSTEM") == 'Linux'
