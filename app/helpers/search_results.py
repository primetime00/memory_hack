from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Union

from app.helpers.aob_value import AOBValue
from app.helpers.search_value import SearchValue

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]
class SearchResults:
    directory = Path('.memory')
    dump_index = 0
    cap = 400000
    increments = 100000

    def __init__(self, name='default', c_type=ctypes.c_int32):
        self.total_results = 0
        self.memory_results = []
        self.file_result_names = []
        self.name = name
        self.signed = c_type in [ctypes.c_int8, ctypes.c_int16, ctypes.c_int32, ctypes.c_int64]
        self.store_size = ctypes.sizeof(c_type)
        self.store_type = c_type

        self.iter_index = 0
        self.last_index = 0
        self.iter_buffer = []


    def __len__(self):
        return self.total_results

    def __getitem__(self, subscript):
        if isinstance(subscript, slice):
            return self.get(subscript.start, subscript.stop)
        else:
            return self.get(subscript, subscript+1)[0]

    def __iter__(self):
        self.iter_index = 0
        self.last_index = 0
        if not self.file_result_names:
            self.iter_buffer = self.memory_results
            self.last_index = 0
        else:
            self.iter_buffer = self.get(0, SearchResults.increments)
            self.last_index = 0
        return self

    def __next__(self):
        if self.iter_index >= self.total_results:
            raise StopIteration()
        if self.iter_index-self.last_index >= len(self.iter_buffer):
            self.last_index += len(self.iter_buffer)
            self.iter_buffer = self.get(self.last_index, self.last_index+SearchResults.increments)
        n = self.next()
        self.iter_index += 1
        return n

    def next(self):
        n = self.iter_buffer[self.iter_index-self.last_index]
        return n

    def add(self, addr: int, value: ctypes_buffer_t):
        r = {'address': addr, 'value': value}
        self.add_r(r)

    def add_r(self, r):
        self.memory_results.append(r)
        self.total_results += 1
        if len(self.memory_results) >= SearchResults.cap:
            self.dump()
            self.memory_results.clear()

    def extend(self, sr: SearchResults):
        self.total_results += (sr.total_results - len(sr.memory_results))
        for r in sr.memory_results:
            self.add_r(r)
        self.file_result_names.extend(sr.file_result_names)

    def dump(self):
        self.directory.mkdir(exist_ok=True)
        if SearchResults.dump_index+1 > 0xFFFF:
            SearchResults.dump_index = 0
        pt = self.directory.joinpath('results_{}_{:04}_{}_{}.res'.format(self.name, self.dump_index, self.store_size, len(self.memory_results)))
        SearchResults.dump_index += 1
        with open(pt, 'wb') as f:
            for r in self.memory_results:
                b1 = r['address'].to_bytes(8, sys.byteorder)
                b2 = bytes(r['value'])
                f.write(b1+b2)
        self.file_result_names.append(str(pt.absolute()))



    def get(self, start, end):
        res = []
        is_start = True
        size_count = 0
        end_file = ""
        start_file = ""
        start_index = -1
        end_index = -1
        total_files_size = self.total_results - len(self.memory_results)
        if not start:
            start = 0
        if not end:
            end = self.total_results if start >= 0 else 0
        if (start ^ end >= 0) and end <= start:
            return []
        elif end <= start:
            end += self.total_results
            if end <= 0:
                return []

        if start >= self.total_results:
            raise IndexError
        if start < 0:
            sz = end-start
            start = self.total_results-(start*-1)
            if start < 0:
                raise IndexError
            end = start+sz
        if not self.file_result_names:
            return self.memory_results[start:end]

        if start >= total_files_size:
            return self.memory_results[start-total_files_size:end-total_files_size]

        for f in self.file_result_names:
            file_result_count = int(f[f.rindex('_') + 1:f.rindex('.')])
            size_count += file_result_count
            if size_count < start:
                continue
            if is_start:
                start_file = f
                start_index = start+file_result_count-size_count
                is_start = False
            if size_count >= end:
                end_file = f
                end_index = end+file_result_count-size_count
                break
        if start_file and start_file == end_file:
            return self._read(start_file, start_index, end_index)

        file_start = self.file_result_names.index(start_file)
        file_end = self.file_result_names.index(end_file)+1 if end_file else len(self.file_result_names)

        for i in range(file_start, file_end):
            if i == file_start:
                res.extend(self._read(self.file_result_names[file_start], start_index))
            elif i == file_end-1:
                res.extend(self._read(self.file_result_names[file_end-1], 0, end_index))
            else:
                res.extend(self._read(self.file_result_names[i], 0))

        if not end_file:
            res.extend(self.memory_results[0:(end-start)-len(res)])

        return res

    def _read(self, file, start=0, end=-1):
        index = 0
        res = []
        with (open(file, 'rb')) as f:
            f.seek((8+self.store_size)*start)
            while end == -1 or index < end-start:
                buf = f.read(8)
                if not buf:
                    break
                addr = int.from_bytes(bytes(buf), byteorder=sys.byteorder)
                value = self.store_type(int.from_bytes(bytes(f.read(self.store_size)), byteorder=sys.byteorder))
                index += 1
                res.append({'address': addr, 'value': value})
        return res

    def copy(self):
        sr = SearchResults(self.name)
        sr.total_results = self.total_results
        sr.memory_results = self.memory_results.copy()
        sr.file_result_names = self.file_result_names.copy()
        return sr

    def get_type(self):
        return self.store_type

    def clear(self):
        self.memory_results.clear()
        for f in self.file_result_names:
            os.unlink(f)
        self.total_results = 0

    @classmethod
    def fromValue(cls, value: SearchValue, name='default'):
        return SearchResults(name=name, c_type=value.get_type())

    def convert_value(self, value: str):
        tp = self.get_type()
        if type(ctypes.Array) == type(tp):
            aob = AOBValue(value)
            return tp(*bytes(aob.aob_item['aob_bytes']))
        elif tp == ctypes.c_float:
            return tp(float(value))
        else:
            if value.lower().startswith("0x"):
                return tp(int(value,16))
            return tp(int(value))








