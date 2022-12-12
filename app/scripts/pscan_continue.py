import json
import re
from pathlib import Path
from queue import Queue
from threading import Thread

import psutil

from app.helpers.data_store import DataStore
from app.helpers.directory_utils import scripts_memory_directory
from app.helpers.exceptions import BreakException
from app.helpers.process.base_address import get_address_base, get_process_map
from app.helpers.timer import PollTimer
from app.script_common import BaseScript
from app.script_ui import BaseUI, Button, Select, Input, MultiSelect
from app.search.operations import Between
from app.search.searcher_multi import SearcherMulti
from app.search.value import Value


class Test(BaseScript):

    def on_load(self):
        pass

    def get_name(self):
        return "Pointer Search"

    def get_app(self):
        return []

    def build_ui(self):
        self.add_ui_element(Select("PROCS", "Process", values=[('none', "None")], on_changed=self.ctrl_changed, children=[Button("REFRESH", "Refresh", on_pressed=self.refresh_pid)]))
        self.add_ui_element(Select("FILES", "Pointer File", values=[('none', "None")], on_changed=self.ctrl_changed))
        self.add_ui_element(Input("OFFSET", "Offset", on_changed=self.ctrl_changed, change_on_focus=False, validator=self.offset_validator, default_text="4096"))
        self.add_ui_element(MultiSelect("REGIONS", "Regions", on_changed=self.ctrl_changed, values=[(str(x), str(x)) for x in range(1, 7)]))
        self.add_ui_element(Button("SEARCH", "Search", on_pressed=self.ctrl_pressed))
        self.add_ui_element(Button("STOP", "Stop", on_pressed=self.ctrl_pressed))

        self.refresh_pid(self.get_ui_control("PROCS"))
        self.populate_files()

        [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['FILES', 'SEARCH', 'STOP']]


    def refresh_pid(self, ele: BaseUI):
        procs = [(x,x) for x in DataStore().get_service('process').get_process_list()]
        procs.insert(0, ('_null', ''))
        self.get_ui_control("PROCS").set_values(procs)

    def populate_files(self):
        f_list = [('_null', '')]
        for f in Path(scripts_memory_directory).glob("*.ptr"):
            f_list.append((str(f.name), str(f.name)))
        self.get_ui_control("FILES").set_values(f_list)

    def find_regions(self):
        region_list = []
        region_set = []
        pm = get_process_map(self.memory.pid, writeable_only=False)
        for p in pm:
            if 'r' not in p['privileges']:
                continue
            pathname = p['pathname']
            if pathname not in region_set:
                if len(pathname) == 0:
                    region_list.append({'select': pathname, 'display': 'anonymous regions'})
                else:
                    display_name = pathname
                    if '/' in pathname:
                        display_name = pathname.split('/')[-1]
                    region_list.append({'select': pathname, 'display': display_name})
                region_set.append(pathname)
        region_list.insert(0, {'select': '_all', 'display': 'All Regions'})
        region_list = self.sort_regions(region_list)
        self.get_ui_control("REGIONS").set_values(region_list)
        self.get_ui_control("REGIONS").set_value('_all')

    def sort_regions(self, region_list):
        proc_exe = psutil.Process(self.memory.pid).exe()
        for region in region_list:
            if region['select'].endswith(proc_exe):
                region['weight'] = 10
            elif region['select'] == '_all':
                region['weight'] = 11
            elif region['select'] == '[heap]':
                region['weight'] = 9
            elif proc_exe in region['select']:
                region['weight'] = 8
            elif region['select'].startswith('/home'):
                region['weight'] = 7
            elif region['select'].startswith('/app/bin'):
                region['weight'] = 6
            elif region['select'].startswith('/usr/bin'):
                region['weight'] = 5
            elif len(region['select']) == 0:
                region['weight'] = 4
            elif region['select'].startswith('/app'):
                region['weight'] = 3
            elif region['select'].startswith('/usr'):
                region['weight'] = 2
            else:
                region['weight'] = 1
        return [(x['select'], x['display']) for x in sorted(region_list, key=lambda x: x['weight'], reverse=True)]

    def offset_validator(self, txt: str):
        try:
            v = int(txt.strip())
            return 0 <= v <= 0xFFFF
        except:
            return False

    def ctrl_changed(self, ele: BaseUI, value):
        if ele.get_name() == 'OFFSET':
            self.check_for_start()
        elif ele.get_name() == 'FILES':
            self.check_for_start()
        elif ele.get_name() == 'PROCS':
            DataStore().get_service('script').set_app(self.get_ui_control("PROCS").get_selection())
            self.put_data('APP_NAME', self.get_ui_control("PROCS").get_selection())
            if value != '_null':
                [self.get_ui_control(ctrl_name).show() for ctrl_name in ['FILES']]
                self.put_data('SEARCHER', SearcherMulti(self.get_memory(), directory=scripts_memory_directory, write_only=False))
                self.find_regions()
            else:
                self.put_data('SEARCHER', None)
                [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['FILES', 'SEARCH', 'STOP']]

    def check_for_start(self):
        if self.get_ui_control("FILES").get_selection() != '_null' and \
                0 <= int(self.get_ui_control("OFFSET").get_text()) <= 0xFFFF and \
                self.get_ui_control("REGIONS").get_selection():
            self.get_ui_control("SEARCH").show()
        else:
            self.get_ui_control("SEARCH").hide()

    def ctrl_pressed(self, ele: BaseUI):
        if ele.get_name() == 'SEARCH':
            self.prepare_search()
        elif ele.get_name() == 'STOP':
            self.stop_search()

    def address_validator(self, txt: str):
        if re.match(r'^[0-9A-F]{0,16}$', txt.upper().strip()):
            return True
        return False

    def frame(self):
        queue: Queue = self.get_data("QUEUE")
        if queue:
            while not queue.empty():
                dt = queue.get()
                if dt == "SUCCESS":
                    self.search_complete()
                elif dt == "BREAK":
                    self.search_break()

    def stop_search(self):
        searcher: SearcherMulti = self.get_data('SEARCHER')
        print('cancel!')
        searcher.cancel()

    def search_break(self):
        print("search cancelled")
        self.put_data('SEARCHER', SearcherMulti(self.get_memory(), directory=scripts_memory_directory, write_only=False))
        self.get_ui_control("STOP").hide()
        self.get_ui_control("SEARCH").show()
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['PROCS', 'FILES']]


    def search_complete(self):
        print("search complete")
        self.get_ui_control("STOP").hide()
        self.get_ui_control("SEARCH").show()
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['PROCS', 'FILES']]


    def prepare_search(self):
        file = self.get_ui_control("FILES").get_selection()
        offset = int(self.get_ui_control("OFFSET").get_text())
        regions = self.get_ui_control("REGIONS").get_selection()


        self.put_data("QUEUE", Queue())

        [self.get_ui_control(ctrl_name).disable() for ctrl_name in ['PROCS', 'FILES']]

        self.get_ui_control("SEARCH").hide()
        self.get_ui_control("STOP").show()

        search_thread = Thread(target=self.search, args=(file, offset, regions, self.get_data("QUEUE")))
        search_thread.start()

    def _find_address(self, ptr, pm):
        for process in pm:
            if process['pathname'] == ptr['path'] and process['map_index'] == ptr['node']:
                return process['start'] + ptr['base_offset']
        return None

    def is_static_address(self, address: int, node_bounds: list):
        return any(x[0] <= address <= x[1] for x in node_bounds)

    def is_valid_address(self, address: int, valid_bounds: list):
        return any(x[0] <= address <= x[1] for x in valid_bounds)

    def perform_search(self, data, offset):
        s: SearcherMulti = self.get_data('SEARCHER')
        poll_timer = PollTimer(10)
        proc_map = list(get_process_map(self.memory.pid, writeable_only=False))
        node_bounds = [(x['start'], x['stop']) for x in proc_map if x['inode'] != '0']
        valid_bounds = [(x['start'], x['stop']) for x in proc_map]
        result_counter = 0
        static_counter = 0
        address_set = set()
        broke = False
        while True:
            new_items = []
            try:
                data_size = len(data)
                for item_index in range(data_size-1, -1, -1):
                    found = False
                    item = data[item_index]
                    s.search_memory_operation(Between((item['address'] - offset, item['address'])))
                    for r in s.results:
                        if poll_timer.has_elapsed():
                            print("Found {} new results with {} static.".format(result_counter, static_counter))
                        if not self.is_valid_address(r['address'], valid_bounds):
                            continue
                        static_result = self.is_static_address(r['address'], node_bounds)
                        if r['address'] in address_set and not static_result:
                            continue
                        if not found:
                            found = True
                            data.pop()
                        result_counter += 1
                        if static_result:
                            static_counter += 1
                        address_set.add(r['address'])
                        base = get_address_base(self.get_memory().pid, r['address'])
                        pathname = base['pathname'] if base['pathname'] != "" else "anon"
                        node = base['map_index']
                        base_offset = r['address'] - base['start']

                        new_item = {"address": r['address'], "path": pathname, "node": node, "base_offset": base_offset,
                                    "offsets": [item['address'] - int.from_bytes(r['value'], byteorder="little", signed=False)] + item['offsets']}
                        new_items.append(new_item)
                if not new_items:
                    break
                data.extend(new_items)
            except BreakException:
                broke = True
                data.extend(new_items)
                break
        return broke, data

    def search(self, file, offset, regions, queue):
        searcher: SearcherMulti = self.get_data('SEARCHER')
        searcher.set_results(value=Value.create("0", "byte_8"))
        searcher.set_search_size("byte_8")
        path = Path(scripts_memory_directory).joinpath(file)
        print(str(path.absolute()), path.exists())
        with path.open(mode='rt') as f:
            orig_data = json.load(f)

        data = orig_data.copy()
        data.reverse()
        if '_all' not in regions:
            searcher.set_include_paths(regions)

        broke, results = self.perform_search(data, offset)

        with Path(scripts_memory_directory.joinpath("sike.ptr")).open("wt") as f:
            json.dump(results, f, indent=4)

        if broke:
            queue.put("BREAK")
        else:
            queue.put("SUCCESS")
