import ctypes
from typing import List, Union

import mem_edit
from mem_edit import Process

from app.helpers.directory_utils import memory_directory
from app.helpers.search_results import SearchResults
from app.script_common.aob import AOB
from app.search.searcher import Searcher
from app.search.searcher_multi import SearcherMulti
from app.helpers.exceptions import BreakException

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]

class ScriptUtilities:
    def __init__(self, mem: mem_edit.Process, name: str, multi:bool = True):
        self.name = name
        self.multi = multi
        self.process = mem
        self.searcher: Searcher = None


    def search_aob(self, aob: AOB):
        if self.searcher is None:
            self.create_searcher()
        self.searcher.set_search_size('array')
        self.searcher.search_memory_value(aob.get_aob_string())
        if len(self.searcher.results) == 0:
            return []
        return [x['address'] for x in self.searcher.results[0:40]]

    def compare_aob(self, aob: AOB):
        if self.searcher is None:
            self.create_searcher()
        size = aob.aob.aob_item['size']
        values = aob.aob.aob_item['aob_bytes']
        bases = []
        for base in aob.get_bases():
            found = True
            try:
                buf = self.process.read_memory(base, (ctypes.c_ubyte * size)())
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
        if self.searcher is None:
            self.create_searcher()
        for start, stop in mem.list_mapped_regions(True):
            try:
                region_buffer = (ctypes.c_byte * (stop - start))()
                mem.read_memory(start, region_buffer)
                if filter_func:
                    found += [x for x in self._haystack_search(aob.aob.get_search_value(), region_buffer, filter_func=filter_func, filter_args=filter_args, offset=start)]
                else:
                    found += [x for x in self._haystack_search(aob.aob.get_search_value(), region_buffer, offset=start)]
            except OSError:
                pass
        return found

    def search_aob_all_memory(self, aob: AOB, single_process=False) -> List:
        if self.searcher is None:
            self.create_searcher()
        self.searcher.set_single_process(single_process)
        try:
            self.searcher.search_memory_value(aob.get_aob_string())
        except BreakException:
            return []
        aob.set_last_searched()
        with self.searcher.results.db() as conn:
            res = self.searcher.results.get_results(conn, _count=20).fetchall()
            if len(res) == 0:
                return []
            return [x[0] for x in res]

        #return self.search_all_memory(mem, aob, filter_func=self._filter if aob.has_wildcards() else None, filter_args=aob)

    def compare_aob2(self, mem:Process, addr:int, aob:AOB):
        res = True
        size = aob.aob.aob_item['size']
        values = aob.aob.aob_item['aob_bytes']
        new_values = []
        try:
            mem = mem.read_memory(addr, (ctypes.c_ubyte * size)())
        except OSError:
            return False, ['invalid'], aob.aob.aob_item['aob_string']
        for i in range(0, len(mem)):
            new_values.append('{0:0{1}X}'.format(mem[i], 2))
            if values[i] > 255:
                continue
            if res and values[i] != mem[i]:
                res = False
        return res, new_values, aob.aob.aob_item['aob_string']

    def create_searcher(self):
        if self.multi:
            self.searcher = SearcherMulti(self.process, results=SearchResults(db_path=memory_directory.joinpath("{}.db".format(self.name))))
        else:
            self.searcher = Searcher(self.process, results=SearchResults(db_path=memory_directory.joinpath("{}.db".format(self.name))))
        self.searcher.set_search_size('array')

    def cancel(self):
        if self.searcher:
            self.searcher.cancel()