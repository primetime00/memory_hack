import re

import mem_edit

from app.helpers.memory_hack_exception import MemoryHackException
from app.helpers.process import get_process_map


class BaseConvertException(MemoryHackException):
    pass

class BaseConvert:
    def __init__(self):
        self.base_lookup_map = {}
        self.process_map = None

    def convert(self, mem: mem_edit.Process, addr: str, include_paths = []):
        if addr in self.base_lookup_map:
            return self.base_lookup_map[addr]
        if ':' not in addr:
            self.base_lookup_map[addr] = int(addr, 16)
            return self.base_lookup_map[addr]

        base_data = re.split(':|\+', addr)
        base_lk = base_data[0] + ':' + base_data[1]
        if base_lk in self.base_lookup_map:
            self.base_lookup_map[addr] = self.base_lookup_map[base_lk] + int(base_data[2], 16)
            return self.base_lookup_map[addr]

        if self.process_map is None:
            self.process_map = get_process_map(mem, writeable_only=False, include_paths=include_paths)
        match = [x for x in self.process_map if x['pathname'].endswith(base_data[0]) and x['map_index'] == int(base_data[1])]
        if len(match) == 0:
            raise BaseConvertException("Could not find base of {}".format(addr))
        self.base_lookup_map[base_lk] = match[0]['start']
        self.base_lookup_map[addr] = match[0]['start']+int(base_data[2], 16)
        return self.base_lookup_map[addr]
