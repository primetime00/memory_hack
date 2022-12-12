from __future__ import annotations

import ctypes
import os
import sys
import time
from typing import Union

from app.helpers.directory_utils import memory_directory

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]
cap = 400000
increments = 100000


class SearchResults:
    directory = memory_directory
    dump_index = 0

    def __init__(self, name='default', store_size=4, cap=cap, increments=increments):
        self.total_results = 0
        self.memory_results = []
        self.file_result_names = []
        self.name = name
        self.store_size = store_size
        self.cap = cap
        self.increments = increments

        self.iter_index = 0
        self.last_index = 0
        self.iter_buffer = []

    def __len__(self):
        return self.total_results

    def __getitem__(self, subscript):
        if isinstance(subscript, slice):
            if self.total_results == 0:
                return []
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
            self.iter_buffer = self.get(0, self.increments)
            self.last_index = 0
        return self

    def __next__(self):
        if self.iter_index >= self.total_results:
            raise StopIteration()
        if self.iter_index-self.last_index >= len(self.iter_buffer):
            self.last_index += len(self.iter_buffer)
            self.iter_buffer = self.get(self.last_index, self.last_index+self.increments)
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
        if len(self.memory_results) >= self.cap:
            self.dump()
            self.memory_results.clear()

    def extend(self, sr: SearchResults):
        self.total_results += (sr.total_results - len(sr.memory_results))
        for r in sr.memory_results:
            self.add_r(r)
        self.memory_results.sort(key=lambda x: x['address'], reverse=True)
        self.file_result_names.extend(sr.file_result_names)

    def dump(self):
        self.directory.mkdir(exist_ok=True)
        if SearchResults.dump_index+1 > 0xFFFF:
            SearchResults.dump_index = 0
        pt = self.directory.joinpath('results_{}_{:04}_{}_{}_{:04}.res'.format(self.name, self.dump_index, self.store_size, len(self.memory_results), int(time.time()*1000) % 9999))
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
            parts = f.split("_")
            file_result_count = int(parts[-2])
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
                value = bytes(f.read(self.store_size))
                index += 1
                res.append({'address': addr, 'value': value})
        return res

    def copy(self):
        sr = SearchResults(self.name)
        sr.cap = self.cap
        sr.increments = self.increments
        sr.total_results = self.total_results
        sr.memory_results = self.memory_results.copy()
        sr.file_result_names = self.file_result_names.copy()
        sr.store_size = self.store_size
        return sr

    @staticmethod
    def from_result(result: SearchResults, store_size=None):
        sr = SearchResults(result.name)
        sr.cap = result.cap
        sr.increments = result.increments
        if not store_size:
            sr.store_size = result.store_size
        else:
            sr.store_size = store_size
        return sr


    def set_name(self, name):
        self.name = name

    def clear(self):
        self.memory_results.clear()
        for f in self.file_result_names:
            os.unlink(f)
        self.total_results = 0
        self.iter_index = 0
        self.last_index = 0
        self.iter_buffer = []


    @staticmethod
    def clear_all_results():
        for res in SearchResults.directory.glob("*.res"):
            res.unlink(missing_ok=True)







