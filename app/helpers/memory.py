import ctypes
import os
import shutil
from pathlib import Path

import mem_edit

import app.helpers.process_utils as ps
import app.helpers.search_utils as search_utils


class Memory:
    inv = ['root', 'kernoops', 'systemd-resolve', 'systemd-timesync', 'avahi', 'rtkit', 'colord']
    procList = {}
    handle: mem_edit.Process = None
    pid: -1

    size_map = {'byte_1': 1, 'byte_2': 2, 'byte_4': 4}

    def __init__(self):
        self.search_data = {'break': False, 'total': 0, 'current': 0}
        pass

    def is_broke(self):
        return self.search_data['break']

    def get_processes(self):
        return self.procList

    def break_search(self):
        self.search_data['break'] = True

    def get_process(self, name):
        self.handle = None
        self.pid = -1
        self.procList = ps.get_process_list()
        if name not in self.procList:
            raise Exception('Cannot find process')
        self.pid = self.procList[name]
        return mem_edit.Process(self.procList[name])

    def get_search_stats(self):
        return self.search_data['total'], self.search_data['current']


    def open_process(self, name):
        self.handle = None
        self.pid = -1
        self.procList = ps.get_process_list()
        if name not in self.procList:
            raise IOError('Cannot find process')
        self.pid = self.procList[name]
        return mem_edit.Process.open_process(self.procList[name])

    def open_pid(self, pid):
        self.handle = None
        self.pid = pid
        return mem_edit.Process.open_process(pid)


    def find_heap_data(self, process:mem_edit.Process, address: int):
        for start, end in process.list_mapped_regions(True):
            if address < start:
                continue
            if address > end:
                continue
            return start, end
        return -1, -1


    def search_aob(self, aob:str, addresses=None): #format: 00 AA ?? 00 0A ?? 0B
        search_items = []
        values = aob.replace(" ", "").split('??')
        gap = 0
        for i in range(0, len(values)):
            value = values[i]
            if value == '':
                gap += 1
            else:
                byte_array = bytearray.fromhex(value)
                search_items.append({'buffer': (ctypes.c_byte * len(byte_array))(*byte_array), 'gap': gap})
                gap = 1
        return self.handle.search_all_wildcards(search_items, addresses=addresses, search_data=self.search_data)

    def compare(self, addr:int, aob:str):
        res = True
        values = aob.upper().split()
        new_values = []
        mem = self.handle.read_memory(addr, (ctypes.c_byte * len(values))())
        for i in range(0, len(mem)):
            new_values.append(hex((mem[i] + (1 << 8)) % (1 << 8))[2:].upper())
            if values[i] == '??':
                continue
            orig = bytes.fromhex(values[i])
            if res and orig[0] != ((mem[i] + (1 << 8)) % (1 << 8)):
                res = False
        return res, new_values, values

    def search_exact(self, value, addresses=None):
        self.search_data['total'] = -1
        if not addresses:
            self.search_data['total'] = self.get_total_memory()
            return self.handle.search_all_memory(value, search_data=self.search_data)
        return self.handle.search_addresses(addresses, value, search_data=self.search_data)

    def write(self, addr, value):
        self.handle.write_memory(addr, value)

    def read(self, addr, _type):
        return self.handle.read_memory(addr, _type)

    def reset(self):
        self.search_data = {'break': False, 'total': 0, 'current': 0}


    def store_memory(self):
        mem_path = Path('.memory')
        self.search_data['total'] = 0
        self.search_data['current'] = 0
        if mem_path.absolute().exists():
            shutil.rmtree(mem_path.absolute())

        for start, stop in self.handle.list_mapped_regions(True):
            try:
                if self.search_data['break']:
                    return
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.handle.read_memory(start, region_buffer)
                os.makedirs('.memory', exist_ok=True)
                with open('.memory/_mem_{}_{}'.format(start, stop), 'wb') as f:
                    self.search_data['total'] += (stop - start)
                    f.write(bytes(region_buffer))
                    pass
            except OSError:
                pass
                #logger.warn('Failed to read in range  0x{} - 0x{}'.format(start, stop))

    def compare_store(self, value, size, previous_addresses=None):
        sz = self.size_map[size]
        addresses = []
        comparer = search_utils.get_cmp(value)
        self.search_data['current'] = 0
        if previous_addresses:
            self.search_data['total'] = len(previous_addresses)
            for (address, current, first) in previous_addresses:
                try:
                    if self.search_data['break']:
                        return []
                    region_buffer = (ctypes.c_byte*sz)()
                    self.handle.read_memory(address, region_buffer)
                    read_data = bytes(region_buffer)
                    try:
                        nv = int.from_bytes(read_data, byteorder='little')
                    except Exception as e:
                        print('Error {}'.format(sz))
                        print(read_data[0:sz])
                        continue
                    if comparer(nv, current):
                        addresses.append({'address': address, 'first': first, 'current': nv})
                    self.search_data['current'] += 1
                except OSError:
                    pass
        else:
            for start, stop in self.handle.list_mapped_regions(True):
                try:
                    if self.search_data['break']:
                        return []
                    pt = Path('.memory/_mem_{}_{}'.format(start, stop))
                    if not pt.exists():
                        continue
                    print('reading {}'.format(pt))
                    region_buffer = (ctypes.c_byte * (stop - start))()
                    self.handle.read_memory(start, region_buffer)
                    with open(pt, 'rb') as f:
                        byte_data = f.read()
                    live_data = bytes(region_buffer)
                    addresses.extend(self._compare_stream(start, byte_data, live_data, sz, comparer))
                except OSError:
                    pass
        return addresses

    def _compare_stream(self, start, byte_data, live_data, raw_size, comparer):
        addresses = []
        buf_len = len(live_data)-(raw_size-1)
        for i in range(0, buf_len):
            if self.search_data['break']:
                return []
            ov = int.from_bytes(byte_data[i: i+raw_size], byteorder='little')
            nv = int.from_bytes(live_data[i: i+raw_size], byteorder='little')
            if comparer(nv, ov):
                addresses.append({'address': start + i, 'first': ov, 'current': nv})
            self.search_data['current'] += 1
        print('found {} results'.format(len(addresses)))
        return addresses

    def get_total_memory(self):
        t = 0
        for start, end in self.handle.list_mapped_regions():
            t += end-start
        return t








