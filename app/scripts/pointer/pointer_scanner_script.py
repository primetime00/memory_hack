import json
import time
from pathlib import Path
from queue import Queue
from threading import Thread, Event
from typing import cast

import psutil

from app.helpers.exceptions import BreakException
from app.helpers.timer import PollTimer
from app.script_common import SubScript
from app.script_ui import controls
from app.script_ui.validators import address_match, offsets_match
from app.search.operations import Between
from .pointer_scanner_helpers import *


class PointerScanner(SubScript):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_thread: Thread = None

    def get_directory_name(self):
        return 'pointerscanner'


    def build_ui(self, root: controls.Element):
        page: controls.Page = root

        page.add_elements([
            controls.Text("Address:", width="145px"),
            controls.Input(on_change=self.ctrl_changed, id='PS_INPUT_ADDRESS', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='PS_PASTE_ADDRESS')])

        page.add_elements([
            controls.Text("Maximum Offset:", width="145px"),
            controls.Input(on_change=self.ctrl_changed, id='PS_INPUT_MAX_OFFSET', trigger_by_focus=False, text='4096')])

        page.add_elements([
            controls.Text("Negative Offsets:", width="145px"),
            controls.Toggle(on_toggle=self.ctrl_changed, id='PS_TOGGLE_NEGATIVE_OFFSET')])


        page.add_elements([
            controls.Text("Maximum Depth:", width="145px"),
            controls.Select(values=[(str(x), str(x)) for x in range(1, 11)], on_change=self.ctrl_changed, select_index=2, id='PS_SELECT_MAX_DEPTH')])

        page.add_elements([
            controls.Text("Search Regions:", width="145px"),
            controls.MultiSelect(values=[], on_change=self.ctrl_changed, id='PS_SELECT_SEARCH_REGIONS', multi_select=True)])

        page.add_elements([
            controls.Button("Start", on_click=self.start_search, id='PS_BUTTON_START'),
            controls.Button("Stop", on_click=self.stop_search, id='PS_BUTTON_STOP')], id='PS_ROW_START_STOP')

        page.add_elements([controls.Text("...", id='PS_TEXT_STATUS')], id='PS_ROW_STATUS')

    def on_load(self):
        self.put_data('PS_QUEUE', Queue())

    def on_ready(self):
        [self.ui.get_element(x).hide() for x in ['PS_BUTTON_STOP', 'PS_ROW_STATUS']]
        [self.ui.get_element(x).disable() for x in ['PS_BUTTON_START']]

    def on_process_attached(self):
        self.memory_manager.set_write_only(False)

    def on_start(self):
        self.memory_manager.get_searcher().reset()
        [self.ui.get_element(x).set_text("") for x in ['PS_INPUT_ADDRESS']]
        [self.ui.get_element(x).set_text("4096") for x in ['PS_INPUT_MAX_OFFSET']]
        self.find_regions()
        self.ui.get_element('PS_SELECT_MAX_DEPTH').set_select_index(2)
        self.on_ready()

    def on_exit(self):
        s = self.memory_manager.get_searcher()
        s.cancel()
        wait_event = Event()
        while self.search_thread and self.search_thread.is_alive():
            wait_event.wait(0.5)



    def frame(self):
        queue: Queue = self.get_data("PS_QUEUE")
        if queue:
            while not queue.empty():
                dt = queue.get()
                if dt == "SUCCESS":
                    self.search_complete()
                elif dt == "BREAK":
                    self.search_break()
                elif dt == "ZERO":
                    self.search_zero()

    def ctrl_changed(self, name, ele_id, data):
        self.check_for_start()

    def start_search(self, name, ele_id, data):
        regions = self.ui.get_element('PS_SELECT_SEARCH_REGIONS').get_selection()
        address = int(self.ui.get_element("PS_INPUT_ADDRESS").get_text(), 16)
        offset = int(self.ui.get_element("PS_INPUT_MAX_OFFSET").get_text())
        depth = int(self.ui.get_element("PS_SELECT_MAX_DEPTH").get_selection())
        negative_offset = cast(controls.Toggle, self.ui.get_element("PS_TOGGLE_NEGATIVE_OFFSET")).is_checked()

        [self.ui.get_element(ctrl_name).disable() for ctrl_name in ['PS_INPUT_ADDRESS', 'PS_INPUT_MAX_OFFSET', 'PS_SELECT_MAX_DEPTH', 'PS_SELECT_SEARCH_REGIONS', 'PS_TOGGLE_NEGATIVE_OFFSET']]

        self.ui.get_element("PS_BUTTON_START").hide()
        self.ui.get_element("PS_BUTTON_STOP").show()
        self.ui.get_element("PS_TEXT_STATUS").set_text('Searching...')
        self.ui.get_element("PS_ROW_STATUS").show()

        self.search_thread = Thread(target=self._search_thread, args=(address, offset, depth, regions, negative_offset, self.get_data("PS_QUEUE")))
        self.search_thread.start()

    def stop_search(self, name, ele_id, data):
        searcher = self.memory_manager.get_searcher()
        self.ui.get_element("PS_BUTTON_STOP").disable()
        self.ui.get_element("PS_TEXT_STATUS").set_text('Stopping, please wait...')
        searcher.cancel()

    def on_paste(self, name, ele_id, data):
        self.ui.get_element("PS_INPUT_ADDRESS").set_text(self.get_data("PS_CLIPBOARD")['address'])
        self.check_for_start()

    def on_copy(self, name, ele_id, data):
        pass

    def on_clipboard_copy(self, data):
        address = None
        if 'address' in data:
            address = data['resolved'] if 'resolved' in data and not data['resolved'].startswith('?') else data['address']
            self.put_data("PS_CLIPBOARD", {'address': address.upper() if ':' not in address else address})
        self.ui.get_element("PS_PASTE_ADDRESS").show() if address else self.ui.get_element("PS_PASTE_ADDRESS").hide()

    def on_clipboard_clear(self):
        [self.ui.get_element(x).hide() for x in ['PS_PASTE_ADDRESS']]
        self.put_data("PS_CLIPBOARD", None)


    def address_validator(self, txt: str):
        return address_match(txt)

    def offset_validator(self, txt: str):
        return offsets_match(txt)


    def find_regions(self):
        region_list = []
        region_set = []
        pm = self.memory_manager.get_process_map()
        add_region(pm, region_list, region_set)
        region_list.insert(0, {'select': '_all', 'display': 'All Regions'})
        region_list = self.sort_regions(region_list)
        self.ui.get_element("PS_SELECT_SEARCH_REGIONS").set_values(region_list)
        self.ui.get_element("PS_SELECT_SEARCH_REGIONS").set_value('_all')

    def sort_regions(self, region_list):
        proc_exe = psutil.Process(self.memory.pid).exe()
        weigh_regions(proc_exe, region_list)
        return [(x['select'], x['display']) for x in sorted(region_list, key=lambda x: x['weight'], reverse=True)]

    def check_for_start(self):
        addr = self.ui.get_element("PS_INPUT_ADDRESS").get_text()
        offset = self.ui.get_element("PS_INPUT_MAX_OFFSET").get_text()
        if not (self.address_validator(addr) and self.offset_validator(offset)):
            self.ui.get_element("PS_BUTTON_START").disable()
            return
        if len(addr) > 4 and 0 <= int(offset) <= 0xFFFFFF and self.ui.get_element("PS_SELECT_SEARCH_REGIONS").get_selection():
            self.ui.get_element("PS_BUTTON_START").enable()
        else:
            self.ui.get_element("PS_BUTTON_START").disable()

    def _search_thread(self, address: int, offset: int, depth: int, regions: list, negative_offset:bool, queue: Queue):
        searcher = self.memory_manager.get_searcher()
        searcher.set_search_size('byte_8')
        if '_all' not in regions:
            self.memory_manager.set_include_paths(regions)
        broke, results = self._perform_search_thread(address, offset, depth, negative_offset)
        if not broke and len(results) == 0:
            queue.put("ZERO")
            return
        with Path(Path(self.get_directory()).joinpath('{}.ptr'.format(self.get_data('APP_NAME')))).open("wt") as f:
            json.dump(results, f, indent=4)
        if broke:
            queue.put("BREAK")
        else:
            queue.put("SUCCESS")


    def _perform_search_thread(self, address, offset, depth, negative_offset):
        s = self.memory_manager.get_searcher()
        poll_timer = PollTimer(10)
        proc_map = list(self.memory_manager.get_process_map())
        print("Searching {} MB".format(sum([x['size'] for x in proc_map]) / 1000000))
        node_bounds = get_node_bounds(proc_map)
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
            for i in range(0, depth):
                print("Searching level {}".format(i))
                if not first_level:
                    stime = time.time()
                    s.search_memory_operation(Between((address - offset, address + offset if negative_offset else address)))
                    total_search_time += time.time() - stime
                    number_of_searches += 1
                    if len(s.results) == 0:
                        zero_counter += 1
                        return False, []
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
                            self.ui.get_element("PS_TEXT_STATUS").set_text('Search level {}<br>Found {} possible pointers.<br>{} potential static pointers.'.format(i, result_counter, static_counter))
                            print("Found {} result and {} static".format(result_counter, static_counter))
                else:
                    if i - 1 not in lvl_map:  # no more pointers
                        break
                    for p in lvl_map[i - 1]:
                        nx = []
                        stime = time.time()
                        s.search_memory_operation(Between((p['address'] - offset, p['address'] + offset if negative_offset else p['address'])))
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
                            self.ui.get_element("PS_TEXT_STATUS").set_text('Search level {}<br>Found {} possible pointers.<br>{} potential static pointers.'.format(i, result_counter, static_counter))
                            print("Found {} result and {} static {} invalid {} reused {} zero searches".format(result_counter, static_counter, invalid_counter, reuse_counter, zero_counter))
                            print("Number of searches {} / Average search time: {} / Searches per minute: {}".format(number_of_searches, total_search_time / number_of_searches, 60 * number_of_searches / (time.time() - start_time)))
                        p['children'] = nx
        except BreakException:
            broke = True
        holder = []
        self.organize(first_level, holder)
        return broke, holder

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

    def is_static_address(self, address: int, node_bounds: list):
        return any(x[0] <= address <= x[1] for x in node_bounds)

    def is_valid_address(self, address: int, valid_bounds: list):
        return any(x[0] <= address <= x[1] for x in valid_bounds)

    def get_base(self, address):
        pm = self.memory_manager.get_process_map()
        for item in pm:
            if item['start'] <= address <= item['stop']:
                return item
        return None


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
                if not is_heap_path(pathname):
                    holder.append({'address': pointer['address'], 'path': pathname, 'node': node, 'base_offset': base_offset, 'offsets': [pointer['offset']]})
                #else:
                #    holder.append({'address': self.memory_manager.get_base("{:X}".format(pointer['address'])), 'path': pathname, 'node': node, 'base_offset': base_offset, 'offsets': [pointer['offset']]})
        return holder

    def search_break(self):
        self.memory_manager.get_searcher().reset()
        print("search cancelled")
        self.ui.get_element("PS_BUTTON_STOP").enable()
        self.ui.get_element("PS_BUTTON_STOP").hide()
        self.ui.get_element("PS_ROW_STATUS").hide()
        self.ui.get_element("PS_BUTTON_START").show()
        [self.ui.get_element(ctrl_name).enable() for ctrl_name in ['PS_INPUT_ADDRESS', 'PS_INPUT_MAX_OFFSET', 'PS_SELECT_MAX_DEPTH', 'PS_SELECT_SEARCH_REGIONS', 'PS_TOGGLE_NEGATIVE_OFFSET']]

    def search_zero(self):
        self.memory_manager.get_searcher().reset()
        print("No results found")
        self.ui.get_element("PS_BUTTON_STOP").enable()
        self.ui.get_element("PS_BUTTON_STOP").hide()
        self.ui.get_element("PS_TEXT_STATUS").set_text('No pointers found.')
        self.ui.get_element("PS_BUTTON_START").show()
        [self.ui.get_element(ctrl_name).enable() for ctrl_name in ['PS_INPUT_ADDRESS', 'PS_INPUT_MAX_OFFSET', 'PS_SELECT_MAX_DEPTH', 'PS_SELECT_SEARCH_REGIONS', 'PS_TOGGLE_NEGATIVE_OFFSET']]



    def search_complete(self):
        print("search complete")
        self.ui.get_element("PS_BUTTON_STOP").hide()
        self.ui.get_element("PS_ROW_STATUS").hide()
        self.ui.get_element("PS_BUTTON_START").show()
        [self.ui.get_element(ctrl_name).enable() for ctrl_name in ['PS_INPUT_ADDRESS', 'PS_INPUT_MAX_OFFSET', 'PS_SELECT_MAX_DEPTH', 'PS_SELECT_SEARCH_REGIONS', 'PS_TOGGLE_NEGATIVE_OFFSET']]
