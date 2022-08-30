import ctypes
import json
import logging
import os
import re
from pathlib import Path
from threading import Thread

from falcon import Request, Response

from app.helpers import MemoryEditor, DynamicHTML, MemoryHandler
from app.helpers import memory_utils


class AOB(MemoryHandler):
    directory = Path('.aob')

    def __init__(self):
        super().__init__()
        self.aob_search_thread: AOB.AOBSearchThread = None
        self.reset()

    def release(self):
        self.reset()

    def html_main(self):
        return DynamicHTML('resources/aob.html', 2).get_html()

    def is_running(self):
        return self.aob_search_thread is not None and self.aob_search_thread.is_alive()


    def process(self, req: Request, resp: Response):
        resp.status = 200
        aob_type = req.media['type']
        if aob_type == "AOB_STATUS":
            if self.aob_search_thread:
                resp.media = self.aob_search_thread.status
            else:
                resp.media = {'status': 'AOB_SEARCH_IDLE'}
            resp.media['aob_list'] = self.get_all_list()
            resp.media['name'] = self.current_name
            resp.media['address'] = memory_utils.value_to_hex(self.current_address)
            resp.media['range'] = self.current_range
            return
        elif aob_type == "AOB_SEARCH":
            self.handle_aob_search(req, resp)
            return
        elif aob_type == "AOB_GET_FILE":
            self.handle_aob_file(req, resp)
            return
        elif aob_type == "AOB_UPLOAD_FILE":
            self.handle_aob_upload(req, resp)
            resp.media['aob_list'] = self.get_all_list()
            return

    def handle_aob_upload(self, req: Request, resp: Response):
        data: str = req.media['data']
        if not data[0:50].strip().startswith("Process:"):
            resp.media = {'status': 'AOB_ERROR', 'error': 'Not a valid AOB file.'}
            return
        pt = Path(req.media['name'])
        filename: str = pt.stem
        name_list = [item.casefold() for item in self.get_all_list()]
        index = 0
        proposed_filename = filename
        while proposed_filename.casefold() in name_list:
            index += 1
            proposed_filename = "{}-{:03d}".format(filename, index)
        dest = self.directory.joinpath("{}{}".format(proposed_filename, pt.suffix))
        with open(dest, "wt") as fp:
            fp.write(data)
        resp.media = {'status': 'AOB_UPLOAD_COMPLETE', 'name': proposed_filename}

    def handle_aob_search(self, req: Request, resp: Response):
        proc = req.media['process']
        self.current_name = req.media['name']
        is_value = req.media['is_value'] == 'true'

        if self.aob_search_thread and self.aob_search_thread.is_alive():
            logging.error("Starting a new AOB search while one is happening!")
            resp.media = {'status': 'AOB_ERROR', 'error': 'A search is already running.'}
            return

        if not is_value:
            try:
                self.current_address = memory_utils.string_to_address(req.media['address'], True)
            except Exception:
                resp.media = {'status': 'AOB_ERROR', 'error': 'Search address is not valid.'}
                return
            try:
                self.current_range = int(req.media['range'])
            except Exception:
                self.current_range = 65536
        else:
            try:
                if req.media['value'] == "":
                    self.current_value = None
                else:
                    self.current_value_size = MemoryEditor.size_map[req.media['size']]
                    self.current_value = memory_utils.value_to_bytes(req.media['value'], self.current_value_size)
            except Exception:
                resp.media = {'status': 'AOB_ERROR', 'error': 'Search value is not valid.'}
                return

        self.aob_search_thread = AOB.AOBSearchThread(self.memory, proc, self.current_name, self.current_address, self.current_range,
                                                     self.current_value, self.current_value_size, is_value)
        self.aob_search_thread.start()
        resp.media = {'status': 'AOB_SEARCH_RUNNING'}

    def handle_aob_file(self, req: Request, resp: Response):
        #is this an aob, int, or both?
        aob_file = self.directory.joinpath("{}.aob".format(req.media['name']))
        int_file = self.directory.joinpath("{}.int".format(req.media['name']))
        address_search = False
        value_search = False
        if int_file.exists():
            address_search = True
        data = ""
        count = 0
        if aob_file.exists():
            value_search = True
            with open(aob_file, "rt") as fp:
                data = fp.read()
            lines = data.split('\n')
            for l in lines:
                if l.startswith('Valid:'):
                    count = int(l[7:])
                    if count == 0:
                        address_search = False
                        value_search = False
                        break
                if l.startswith('Searched:'):
                    address_search = l[10:] != 'True'
                if l.startswith('Size:'):
                    break
        #self.current_name = req.media['name']
        resp.media = {'status': 'AOB_FILE_DATA', 'data': data, 'count': count, 'address_search': address_search, 'value_search': value_search}

    def get_name_list(self):
        return [x.stem for x in AOB.directory.glob('*.int')]

    def get_aob_list(self):
        return [x.stem for x in AOB.directory.glob('*.aob')]

    def get_all_list(self):
        return list(set(self.get_name_list()).union(set(self.get_aob_list())))

    def reset(self):
        if self.aob_search_thread and self.aob_search_thread.is_alive():
            self.memory.break_search()
            self.aob_search_thread.stop = True
            self.aob_search_thread.join()

        self.current_name = ""
        self.current_address = 0
        self.current_range = 0
        self.current_value = None
        self.current_value_size = None
        self.aob_search_thread: AOB.AOBSearchThread = None


    class AOBSearchThread(Thread):
        largest_run = 35
        smallest_run = 7
        consecutive_zeros = 5
        pattern = re.compile('^Size: (\d+)\s*Offset: (-?[0-9A-F]+)\s*([0-9A-F ]+)$')

        def __init__(self, _memory, _process, _name, _address, _range, _value, _size, _is_value):
            super().__init__(target=self.process)
            self.stop = False
            self.memory = _memory
            self.current_process = _process
            self.current_name = _name
            self.current_address = _address
            self.current_range = _range
            self.current_value = _value if _value else None
            self.current_size = _size
            self.is_value = _is_value
            if self.current_range % 2 != 0:
                self.current_range += 1
            if not AOB.directory.exists():
                os.mkdir(AOB.directory)
            self.aob_file_name = AOB.directory.joinpath('{}.int'.format(self.current_name))
            self.aob_match_file = AOB.directory.joinpath('{}.aob'.format(self.current_name))
            self.current_aobs = []
            self.status = {'status': 'AOB_IDLE'}

        def calculate_range(self, proc):
            start, end = self.memory.find_heap_data(proc, self.current_address)
            if start == -1:
                return start, end
            want_start = self.current_address - int((self.current_range / 2))
            if want_start > start:
                start = want_start
            want_end = self.current_address + int((self.current_range / 2))
            if want_end < end:
                end = want_end
            actual_range = end - start
            self.current_range = actual_range
            return start, end


        def process_address_run(self):
            if not self.aob_file_name.exists():
                # start needs to be an address
                start, end = self.calculate_range(self.memory.handle)
                if start == -1:  # error with range
                    self.status = {'status': 'AOB_ERROR', 'error': "Invalid address for this process."}
                    return
                data = self.memory.read(start, (ctypes.c_byte * (end - start))())
                with open(self.aob_file_name, 'wt') as i_file:
                    json.dump(
                        {'process': self.current_process, 'name': self.current_name, 'range': self.current_range,
                         'start': start, 'end': end, 'iteration': 0}, i_file)
                with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)), 'wb') as d_file:
                    d_file.write(data)
                self.status = {'status': 'AOB_ADDRESS_SEARCH_COMPLETE'}
            else: #we have an .int file, we need an .aob if we are going to check for values
                self.aob_address_search()

        def process_value_run(self):
            if not self.aob_match_file.exists():
                logging.error("Trying to do a value search without an .aob file!")
                return
            self.current_aobs = self.aob_value_search()


        def process(self):
            self.status = {'status': 'AOB_SEARCHING'}
            if not self.is_value:
                self.process_address_run()
            else:
                self.process_value_run()


        def aob_value_search(self):
            aob_groups = []
            with open(self.aob_match_file, "rt") as f:
                for line in f.readlines():
                    if not line.startswith('Size: '):
                        continue
                    matches = re.match(self.pattern, line)
                    size = int(matches.group(1))
                    offset = int(matches.group(2).replace(' ', ''), 16)
                    aob = matches.group(3)
                    aob_groups.append((size, offset, aob))
            index = 0
            total = len(aob_groups)
            for i in range(len(aob_groups) - 1, -1, -1):
                self.status['progress'] = round(100.0 * index / total, 1)
                if self.stop:
                    self.status = {'status': 'AOB_SEARCH_IDLE'}
                    return []
                index += 1
                aob_item = aob_groups[i]
                addrs = self.memory.search_aob(aob_item[2])
                if len(addrs) != 1:
                    aob_groups.remove(aob_item)
                    continue
                if self.current_value:
                    address = addrs[0] - aob_item[1]
                    read = self.memory.read(address, (ctypes.c_byte * self.current_size)())
                    if read[0:] != self.current_value[0:]:
                        aob_groups.remove(aob_item)
                        continue
            self.status = {'status': 'AOB_VALUE_SEARCH_COMPLETE', 'possible_aobs': len(aob_groups)}
            self.write(aob_groups)
            return aob_groups


        def aob_address_search(self):
            with open(self.aob_file_name, 'rt') as i_file:
                info = json.load(i_file)
            start = self.current_address - int((info['range'] / 2))
            end = self.current_address + int((info['range'] / 2))
            new_data = self.memory.read(start, (ctypes.c_byte * (end - start))())
            with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)),
                      'rb') as d_file:
                old_data = d_file.read()
                old_data = (ctypes.c_byte * len(old_data))(*old_data)
            with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)),
                      'wb') as d_file:
                d_file.write(new_data)
            with open(self.aob_file_name, 'wt') as i_file:
                json.dump({'process': self.current_process, 'name': info['name'], 'range': info['range'],
                           'start': start, 'end': end, 'iteration': info['iteration'] + 1}, i_file)
            aob_list = self.compare_data(new_data, old_data, start - self.current_address)
            if self.stop:
                self.status = {'status': 'AOB_SEARCH_IDLE'}
                return
            with open(self.aob_match_file, 'wt') as i_file:
                i_file.write("Process: {}\nName: {}\nValid: {}\n\n".format(self.current_process, info['name'],
                                                                           len(aob_list)))
                for aob in aob_list:
                    i_file.write(
                        "Size: {:<5} Offset: {:<15X} {}\n".format(aob['length'], aob['start'], aob['aob']))
            self.status = {'status': 'AOB_ADDRESS_SEARCH_COMPLETE', 'possible_aobs': len(aob_list)}

        def compare_data(self, new_data, old_data, offset):
            data_length = len(new_data)
            aob_table = []
            current_run = 0
            start_run = -1
            for i in range(0, data_length):
                if self.stop:
                    return []
                if new_data[i] == old_data[i] and not self.are_zeros(new_data, old_data, i, data_length):
                    if current_run == 0 and new_data[i] == 0:
                        continue
                    current_run, start_run = self.do_run(start_run, current_run, i, aob_table, offset, new_data)
                else:  # not a run
                    current_run = self.stop_run(start_run, current_run, aob_table, offset, new_data)
            return aob_table

        def stop_run(self, start_run, current_run, aob_table, offset, new_data):
            if current_run >= self.smallest_run:
                b_data = (ctypes.c_byte * current_run)(*new_data[start_run:start_run + current_run])
                aob_table.append(
                    {'start': start_run + offset, 'length': current_run, 'aob': memory_utils.bytes_to_aobstr(b_data)})
            current_run = 0
            return current_run

        def do_run(self, start_run, current_run, i, aob_table, offset, new_data):
            if current_run == 0:
                start_run = i
            current_run += 1
            if current_run == self.largest_run:
                b_data = (ctypes.c_byte * current_run)(*new_data[start_run:start_run + current_run])
                aob_table.append(
                    {'start': start_run + offset, 'length': current_run, 'aob': memory_utils.bytes_to_aobstr(b_data)})
                current_run = 0
            return current_run, start_run

        def are_zeros(self, new_data, old_data, i, data_length):
            if i+self.consecutive_zeros >= data_length:
                return False
            if new_data[i: i+self.consecutive_zeros] == old_data[i: i+self.consecutive_zeros]:
                return new_data[i: i+self.consecutive_zeros] == [0]*self.consecutive_zeros or new_data[i: i+self.consecutive_zeros] == [-1]*self.consecutive_zeros
            return False

        def write(self, aobs):
            with open(self.aob_match_file, 'wt') as i_file:
                i_file.write("Process: {}\nName: {}\nValid: {}\nSearched: true\n\n".format(self.current_process, self.current_name, len(aobs)))
                for aob in aobs:
                    i_file.write("Size: {:<5} Offset: {:<15X} {}\n".format(aob[0], aob[1], aob[2]))

