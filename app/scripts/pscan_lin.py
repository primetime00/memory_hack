import json
import re
import time
from pathlib import Path
from queue import Queue
from threading import Thread

import psutil

from app.helpers.data_store import DataStore
from app.helpers.directory_utils import scripts_memory_directory
from app.helpers.exceptions import BreakException
from app.helpers.process.base_address_lin import get_process_map
from app.helpers.timer import PollTimer
from app.script_common import BaseScript
from app.script_ui import BaseUI, Button, Select, Input, MultiSelect, Text
from app.search.operations import Between
from app.search.searcher_multi import SearcherMulti


class PointerScanner(BaseScript):

    def on_load(self):
        pass

    def get_name(self):
        return "Pointer Scan"

    def get_app(self):
        return []

    def build_ui(self):
        self.add_ui_element(Select("PROCS", "Process", values=[('none', "None")], on_changed=self.ctrl_changed, children=[Button("REFRESH", "Refresh", on_pressed=self.refresh_pid)]))
        self.add_ui_element(Input("ADDRESS", "Address", on_changed=self.ctrl_changed, change_on_focus=False, validator=self.address_validator, default_text="", children=[Button("PASTE", "Paste", on_pressed=self.ctrl_pressed)]))
        self.add_ui_element(Input("OFFSET", "Offset", on_changed=self.ctrl_changed, change_on_focus=False, validator=self.offset_validator, default_text="4096"))
        self.add_ui_element(Select("LEVELS", "Levels", on_changed=self.ctrl_changed, values=[(str(x), str(x)) for x in range(1, 7)]))
        self.add_ui_element(MultiSelect("REGIONS", "Regions", on_changed=self.ctrl_changed, values=[(str(x), str(x)) for x in range(1, 7)]))
        self.get_ui_control("LEVELS").set_value("3")
        self.add_ui_element(Button("SEARCH", "Search", on_pressed=self.ctrl_pressed))
        self.add_ui_element(Button("STOP", "Stop", on_pressed=self.ctrl_pressed))
        self.add_ui_element(Text("STATUS", "..."))

        self.refresh_pid(self.get_ui_control("PROCS"))

        [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['ADDRESS', 'OFFSET', 'LEVELS', 'REGIONS', 'SEARCH', 'STOP', 'STATUS', 'PASTE']]


    def refresh_pid(self, ele: BaseUI):
        procs = [(x,x) for x in DataStore().get_service('process').get_process_list()]
        procs.insert(0, ('_null', ''))
        self.get_ui_control("PROCS").set_values(procs)

    def find_regions(self):
        region_list = []
        region_set = []
        pm = get_process_map(self.memory, writeable_only=True)
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

    def ctrl_changed(self, ele: BaseUI, value):
        if ele.get_name() == 'ADDRESS' or ele.get_name() == 'OFFSET' or ele.get_name() == 'LEVELS':
            self.check_for_start()
        elif ele.get_name() == 'PROCS':
            DataStore().get_service('script').set_app(self.get_ui_control("PROCS").get_selection())
            self.put_data('APP_NAME', self.get_ui_control("PROCS").get_selection())
            if value != '_null':
                [self.get_ui_control(ctrl_name).show() for ctrl_name in ['ADDRESS', 'OFFSET', 'LEVELS', 'REGIONS']]
                self.put_data('SEARCHER', SearcherMulti(self.get_memory(), directory=scripts_memory_directory, write_only=True))
                self.find_regions()
                self.check_for_start()
            else:
                self.put_data('SEARCHER', None)
                [self.get_ui_control(ctrl_name).hide() for ctrl_name in ['ADDRESS', 'OFFSET', 'LEVELS', 'REGIONS', 'SEARCH', 'STOP', 'STATUS', 'PASTE']]
        elif ele.get_name() == 'REGIONS':
            self.check_for_start()

    def check_for_start(self):
        if len(self.get_ui_control("ADDRESS").get_text()) > 4 and \
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
        elif ele.get_name() == 'PASTE':
            self.get_ui_control("ADDRESS").set_text("{:X}".format(int(self.get_data("CLIPBOARD"))))

    def address_validator(self, txt: str):
        if re.match(r'^[0-9A-F]{0,16}$', txt.upper().strip()):
            return True
        return False

    def offset_validator(self, txt: str):
        try:
            v = int(txt.strip())
            return 0 <= v <= 0xFFFF
        except:
            return False

    def on_clipboard_copy(self, data):
        if 'address' in data:
            self.get_ui_control("PASTE").show()
            self.put_data("CLIPBOARD", data['address'])

    def on_clipboard_clear(self):
        self.get_ui_control("PASTE").hide()

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
        self.get_ui_control("STOP").disable()
        self.get_ui_control("STATUS").set_text('Stopping, please wait...')
        print('cancel!')
        searcher.cancel()

    def search_break(self):
        self.get_data('SEARCHER').reset()
        print("search cancelled")
        self.get_ui_control("STOP").enable()
        self.get_ui_control("STOP").hide()
        self.get_ui_control("STATUS").hide()
        self.get_ui_control("SEARCH").show()
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['PROCS', 'REFRESH', 'ADDRESS', 'OFFSET', 'LEVELS', 'REGIONS']]


    def search_complete(self):
        print("search complete")
        self.get_ui_control("STOP").hide()
        self.get_ui_control("STATUS").hide()
        self.get_ui_control("SEARCH").show()
        [self.get_ui_control(ctrl_name).enable() for ctrl_name in ['PROCS', 'REFRESH', 'ADDRESS', 'OFFSET', 'LEVELS', 'REGIONS']]



    def prepare_search(self):
        address = int(self.get_ui_control("ADDRESS").get_text(), 16)
        offset = int(self.get_ui_control("OFFSET").get_text())
        levels = int(self.get_ui_control("LEVELS").get_selection())
        regions = self.get_ui_control("REGIONS").get_selection()

        self.put_data("QUEUE", Queue())

        [self.get_ui_control(ctrl_name).disable() for ctrl_name in ['PROCS', 'REFRESH', 'ADDRESS', 'OFFSET', 'LEVELS', 'REGIONS']]

        self.get_ui_control("SEARCH").hide()
        self.get_ui_control("STOP").show()
        self.get_ui_control("STATUS").set_text('Searching...')
        self.get_ui_control("STATUS").show()

        search_thread = Thread(target=self.search, args=(address, offset, levels, regions, self.get_data("QUEUE")))
        search_thread.start()

    def generate_base_map(self, regions):
        if '_all' in regions:
            pm = get_process_map(self.memory)
        else:
            pm = get_process_map(self.memory, include_paths=regions)

        self.put_data("PROCESS_MAP", pm)

    def get_base(self, address):
        pm = self.get_data("PROCESS_MAP")
        for item in pm:
            if item['start'] <= address <= item['stop']:
                return item
        return None


    def search(self, address, offset, levels, regions, queue):
        searcher: SearcherMulti = self.get_data('SEARCHER')
        searcher.set_search_size("byte_8")
        if '_all' not in regions:
            searcher.set_include_paths(regions)
        self.generate_base_map(regions)
        broke, results = self.perform_search(address, offset, levels)
        with Path(scripts_memory_directory.joinpath('{}.ptr'.format(self.get_data('APP_NAME')))).open("wt") as f:
            json.dump(results, f, indent=4)
        if broke:
            queue.put("BREAK")
        else:
            queue.put("SUCCESS")

    def is_static_address(self, address: int, node_bounds: list):
        return any(x[0] <= address <= x[1] for x in node_bounds)

    def is_valid_address(self, address: int, valid_bounds: list):
        return any(x[0] <= address <= x[1] for x in valid_bounds)

    def perform_search(self, address, offset, levels):
        s: SearcherMulti = self.get_data('SEARCHER')
        poll_timer = PollTimer(10)
        proc_map = list(get_process_map(self.memory, writeable_only=True, include_paths=s.get_include_paths()))
        print("Searching {} MB".format(sum([x['size'] for x in proc_map]) / 1000000))
        node_bounds = [(x['start'], x['stop']) for x in proc_map if x['inode'] != '0']
        valid_bounds = [(x['start'], x['stop']) for x in proc_map]
        result_counter = 0
        static_counter = 0
        reuse_counter = 0
        invalid_counter = 0
        zero_counter = 0
        start_time = time.time()
        total_search_time = 0
        number_of_searches = 0
        address_set = set()
        first_level = []
        lvl_map = {}
        broke = False
        try:
            for i in range(0, levels):
                print("Searching level {}".format(i))
                if not first_level:
                    stime = time.time()
                    s.search_memory_operation(Between((address - offset, address)))
                    total_search_time += time.time() - stime
                    number_of_searches += 1
                    if len(s.results) == 0:
                        zero_counter += 1
                    with s.results.db() as conn:
                        all_results = [{'address': x[0], 'value': x[1]} for x in s.results.get_results(conn).fetchall()]
                    result_indexes = self.generate_result_order(all_results)
                    for index in result_indexes:
                        r = all_results[index]
                        if r['address'] not in address_set:
                            if not self.is_valid_address(r['address'], valid_bounds):
                                invalid_counter += 1
                                continue
                            if r['address'] % 4 != 0:
                                continue
                            item = {'address': r['address'], 'offset': address - int.from_bytes(r['value'], byteorder="little", signed=False), 'children': []}
                            result_counter += 1
                            if self.is_static_address(r['address'], node_bounds):
                                static_counter += 1
                            first_level.append(item)
                            address_set.add(r['address'])
                            if i not in lvl_map:
                                lvl_map[i] = []
                            lvl_map[i].append(item)
                        if poll_timer.has_elapsed():
                            self.get_ui_control("STATUS").set_text('Search level {}<br>Found {} possible pointers.<br>{} potential static pointers.'.format(i, result_counter, static_counter))
                            print("Found {} result and {} static".format(result_counter, static_counter))
                else:
                    if i - 1 not in lvl_map:  # no more pointers
                        break
                    for p in lvl_map[i - 1]:
                        nx = []
                        stime = time.time()
                        s.search_memory_operation(Between((p['address'] - offset, p['address'])))
                        total_search_time += time.time() - stime
                        number_of_searches += 1
                        if len(s.results) == 0:
                            zero_counter += 1
                        with s.results.db() as conn:
                            all_results = [{'address': x[0], 'value': x[1]} for x in s.results.get_results(conn).fetchall()]
                        result_indexes = self.generate_result_order(all_results)
                        for index in result_indexes:
                            r = all_results[index]
                            static_address = self.is_static_address(r['address'], node_bounds)
                            valid = (r['address'] % 4 == 0) and (static_address or (r['address'] not in address_set and self.is_valid_address(r['address'], valid_bounds)))
                            if not valid:
                                invalid_counter += 1
                                if r['address'] in address_set:
                                    reuse_counter += 1
                                continue
                            item = {'address': r['address'], 'offset': p['address'] - int.from_bytes(r['value'], byteorder="little", signed=False), 'children': []}
                            result_counter += 1
                            if static_address:
                                static_counter += 1
                            nx.append(item)
                            address_set.add(r['address'])
                            if i not in lvl_map:
                                lvl_map[i] = []
                            lvl_map[i].append(item)
                        if poll_timer.has_elapsed():
                            self.get_ui_control("STATUS").set_text('Search level {}<br>Found {} possible pointers.<br>{} potential static pointers.'.format(i, result_counter, static_counter))
                            print("Found {} result and {} static {} invalid {} reused {} zero searches".format(result_counter, static_counter, invalid_counter, reuse_counter, zero_counter))
                            print("Number of searches {} / Average search time: {} / Searches per minute: {}".format(number_of_searches, total_search_time / number_of_searches, 60 * number_of_searches / (time.time() - start_time)))
                        p['children'] = nx
        except BreakException:
            broke = True
        holder = []
        self.organize(first_level, holder)
        return broke, holder

    def organize(self, pointers, holder):
        for pointer in pointers:
            if pointer['children']:
                ret = self.organize(pointer['children'], [])
                for r in ret:
                    r['offsets'].append(pointer['offset'])
                    holder.append(r)
            else:
                base = self.get_base(pointer['address'])
                pathname = base['pathname'] if base['pathname'] != "" else "anon"
                node = base['map_index']
                base_offset = pointer['address'] - base['start']
                if pathname != '[heap]':
                    holder.append({'address': pointer['address'], 'path': pathname, 'node': node, 'base_offset': base_offset, 'offsets': [pointer['offset']]})
        return holder

    def generate_result_order(self, results):
        v = list(range(0, len(results)))
        g = []
        state = 0
        sz = len(v)
        index = 0
        end_index = len(v) - 1
        while len(g) != sz:
            if state == 0:
                g.append(v[0])
                state = 1
                v.pop(0)
                index += 1
            elif state == 1:
                g.append(v[-1])
                state = 2
                v.pop(len(v) - 1)
                end_index -= 1
            elif state == 2:
                center = int((len(v) - 1) / 2)
                g.append(v[center])
                v.pop(center)
                state = 0
        return g
