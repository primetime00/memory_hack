import ctypes
from typing import Union

from mem_edit import Process

from app.helpers.operation_control import OperationControl
from app.helpers.progress import Progress

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]
class AOBUtilities:
    def __init__(self, mem: Process, op_control: OperationControl, progress:Progress):
        self.mem = mem
        self.op_control = op_control
        self.progress = progress
        self.total_size, self.mem_start, self.mem_end = self.get_total_memory_size()

    def get_total_memory_size(self):
        total = 0
        ls = list(self.mem.list_mapped_regions())
        _start = ls[0][0]
        _end = ls[-1][1]
        for start, stop in self.mem.list_mapped_regions():
            try:
                region_buffer = (ctypes.c_byte * (stop - start))()
                self.mem.read_memory(start, region_buffer)
                total += (stop-start)
            except OSError:
                continue
        return total, _start, _end

    def calculate_range(self, address: int, range: int):
        start, end = self.find_heap_data(self.mem, address)
        if start == -1:
            return start, end
        want_start = address - int((range / 2))
        if want_start % 2 != 0:
            want_start -= 1

        if want_start > start:
            start = want_start
        want_end = address + int((range / 2))
        if want_end % 2 != 0:
            want_end += 1
        if want_end < end:
            end = want_end
        actual_range = end - start
        return start, end, actual_range

    def find_heap_data(self, process: Process, address: int):
        for start, end in process.list_mapped_regions(True):
            if address < start:
                continue
            if address > end:
                continue
            return start, end
        return -1, -1