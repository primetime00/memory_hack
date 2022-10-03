import ctypes
from typing import List, Union

from mem_edit import Process

from app.script_common.aob import AOB

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class ScriptUtilities:
    def __init__(self):
        pass

    def _filter(self, haystack, lcl_offset, glb_offset, args):
        aob: AOB = args
        j = 0
        buf = ctypes.cast(haystack, ctypes.POINTER(ctypes.c_ubyte))
        size = aob.aob.aob_item['size']
        start = lcl_offset - aob.aob.get_offset()
        end = start + size
        if start < 0:
            return None
        if end >= len(haystack):
            return None
        for i in range(start, end):
            bt = aob.aob.aob_item['aob_bytes'][j]
            j += 1
            if bt >= 256:
                continue
            if bt != buf[i]:
                return None
        return {'address': glb_offset + start, 'value': (ctypes.c_ubyte * size)(*buf[start:end])}

    def _haystack_search(self, needle_buffer: ctypes_buffer_t, haystack_buffer: ctypes_buffer_t, filter_func = None, filter_args=None, offset=0) -> List:
        found = []
        haystack = bytes(haystack_buffer)
        needle = bytes(needle_buffer)
        start = 0
        result = haystack.find(needle, start)
        while start < len(haystack) and result != -1:
            if filter_func:
                res = filter_func(haystack_buffer, result, offset, filter_args)
                if res:
                    found.append(res)
            else:
                found.append({'address': result+offset, 'value': needle_buffer})
            start = result + 1
            result = haystack.find(needle, start)
        return found


    def search_all_memory(self, mem: Process, aob: AOB, filter_func = None, filter_args=None) -> List:
        found = []
        for start, stop in mem.list_mapped_regions(True):
            try:
                region_buffer = (ctypes.c_byte * (stop - start))()
                mem.read_memory(start, region_buffer)
                found += [x for x in self._haystack_search(aob.aob.get_search_value(), region_buffer, filter_func=filter_func, filter_args=filter_args, offset=start)]
            except OSError:
                pass
        return found

    def search_aob_all_memory(self, mem: Process, aob: AOB) -> List:
        return self.search_all_memory(mem, aob, filter_func=self._filter, filter_args=aob)

    def compare_aob(self, mem:Process, addr:int, aob:AOB):
        res = True
        size = aob.aob.aob_item['size']
        values = aob.aob.aob_item['aob_bytes']
        new_values = []
        mem = mem.read_memory(addr, (ctypes.c_ubyte * size)())
        for i in range(0, len(mem)):
            new_values.append('{0:0{1}X}'.format(mem[i], 2))
            if values[i] > 255:
                continue
            if res and values[i] != mem[i]:
                res = False
        return res, new_values, aob.aob.aob_item['aob_string']
