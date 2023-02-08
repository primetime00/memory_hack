import ctypes
import re
from pathlib import Path
from typing import Union

import mem_edit

from app.helpers.exceptions import ScriptException
from app.helpers.process import get_process_map
from app.helpers.search_results import SearchResults
from app.script_common.aob import AOB
from app.search.searcher_multi import SearcherMulti

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]
import platform

class MemoryManager:
    re_fn = r'^((?!(?:COM[0-9]|CON|LPT[0-9]|NUL|PRN|AUX|com[0-9]|con|lpt[0-9]|nul|prn|aux)|\s|[\.]{2,})[^\\\/:*"?<>|]{1,254}(?<![\s\.])):(\d+)\+([0-9a-f]+)$'
    arch = platform.system()

    def __init__(self, memory: mem_edit.Process, directory: str, include_paths=[]):
        self.path_cache = {}
        self.memory = memory
        self.directory = directory
        self.write_only: bool = True
        self.regions = []
        if memory is None:
            self.process_map = {}
        else:
            self.process_map = get_process_map(memory, include_paths=include_paths)
        self.searcher_map: {str, SearcherMulti} = {}

    def get_searcher(self, name:str = '_default') -> SearcherMulti:
        if not self.searcher_map.get(name, None):
            search_path = Path(self.directory).joinpath('.search')
            if not search_path.exists():
                search_path.mkdir(exist_ok=True, parents=True)
            self.searcher_map[name] = SearcherMulti(self.memory, write_only=self.write_only, directory=search_path, results=SearchResults(db_path=search_path.joinpath('{}_search.db'.format(name))))
        return self.searcher_map[name]

    def get_process_map(self):
        return self.process_map

    def get_address(self, addr: str):
        if addr in self.path_cache:
            return self.path_cache[addr]
        pm = self.process_map
        if ':' in addr:
            for process in pm:
                matcher = re.match(self.re_fn, addr.strip(), re.IGNORECASE)
                if process['pathname'].endswith(matcher.group(1)) and process['map_index'] == int(matcher.group(2)):
                    res = process['start'] + int(matcher.group(3), 16)
                    self.path_cache[addr] = res
                    return res
            return None
        else:
            return int(addr, 16)

    def get_base_bounds(self, addr):
        cv_addr = self.get_address(addr)
        if not cv_addr:
            return None

        pm = sorted(self.get_process_map(), key=lambda x: x['start'])
        for p in pm:
            if p['start'] <= cv_addr <= p['stop']:
                return p['start'], p['stop']
        return None

    def get_base(self, addr: str):
        cv_addr = self.get_address(addr)
        if not cv_addr:
            return addr

        pm = sorted(self.get_process_map(), key=lambda x: x['start'])
        for p in pm:
            if p['start'] <= cv_addr <= p['stop']:
                offset = cv_addr - p['start']
                if self.arch == 'Linux':
                    stem = p['pathname'].split('/')[-1]
                else:
                    stem = p['pathname'].split('\\')[-1]
                index = p['map_index']
                return '{}:{}+{:X}'.format(stem, index, offset)
        return None

    def read_pointer(self, address: str, offsets: str, return_base: bool = False):
        addr = self.get_address(address)
        if addr is None:
            raise ScriptException("Could not translate address: {}".format(address))
        offset_values = self.string_to_offsets(offsets)
        try:
            offset = 0
            for offset in offset_values:
                read = self.memory.read_memory(addr, ctypes.c_uint64()).value
                read = read + offset
                addr = read
            return addr - offset if return_base else addr
        except Exception:
            return None

    def write_pointer(self, address: str, offsets: str, value: ctypes_buffer_t, error_func: callable = None):
        addr = self.get_address(address)
        if addr is None:
            raise ScriptException("Could not translate address: {}".format(address))
        offset_values = self.string_to_offsets(offsets)
        try:
            for offset in offset_values:
                v = self.memory.read_memory(address, ctypes.c_uint64()).value
                v = v + offset
                address = v
            self.memory.write_memory(address, value)
        except Exception as e:
            if error_func:
                error_func(e)
            return False
        return True



    def offsets_to_string(self, offsets: list):
        return ", ".join("{:X}".format(x) for x in offsets)

    def string_to_offsets(self, offsets: str):
        try:
            return [int(x.strip(), 16) for x in offsets.split(",")]
        except Exception:
            raise ScriptException("Could not translate offsets: {}".format(offsets))

    def set_include_paths(self, regions):
        for searcher in self.searcher_map.values():
            searcher.set_include_paths(regions)
        self.regions = regions
        self.process_map = get_process_map(self.memory, self.write_only, self.regions)

    def set_write_only(self, write_only: bool):
        for searcher in self.searcher_map.values():
            searcher.set_write_only(write_only)
        self.write_only = write_only
        self.process_map = get_process_map(self.memory, self.regions, self.write_only)


    def copy_pointer(self, pointer: dict):
        address = self.get_base('{:X}'.format(pointer['address']))
        offsets = self.offsets_to_string(pointer['offsets'])
        return {'address': address, 'offsets': offsets}

    def compare_aob(self, aob: AOB):
        size = aob.aob.aob_item['size']
        values = aob.aob.aob_item['aob_bytes']
        bases = []
        for base in aob.get_bases():
            found = True
            try:
                buf = self.memory.read_memory(base, (ctypes.c_ubyte * size)())
                for i in range(0, len(buf)):
                    if values[i] > 255:
                        continue
                    if values[i] != buf[i]:
                        found = False
                        break
                if found:
                    bases.append(base)
            except OSError:
                continue
        return bases

