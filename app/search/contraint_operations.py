import ctypes
from app.search.operations import MemoryOperation

class ConstraintOperationFloat(MemoryOperation):
    def __init__(self, low_value, high_value, max_change):
        self.low = low_value
        self.high = high_value
        self.max_change = max_change
        super().__init__()

class IncreaseOperationConstraintFloat(ConstraintOperationFloat):
    def operation(self, *current_and_previous_read):
        diff = current_and_previous_read[0] - current_and_previous_read[1]
        return 0.001 < diff <= self.max_change and self.low <= current_and_previous_read[0] <= self.high

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                diff = r1 - r2
                if 0.001 < diff <= self.max_change and self.low <= r1 <= self.high:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                diff = buf1.ptr[i] - buf2.ptr[i]
                if 0.001 < diff <= self.max_change and self.low <= buf1.ptr[i] <= self.high:
                    result_callback(result_list, i, buf1.ptr[i])

class DecreaseOperationConstraintFloat(ConstraintOperationFloat):
    def operation(self, *current_and_previous_read):
        diff = current_and_previous_read[1] - current_and_previous_read[0]
        return 0.001 < diff <= self.max_change and self.low <= current_and_previous_read[0] <= self.high

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                diff = r2 - r1
                if 0.001 < diff <= self.max_change and self.low <= r1 <= self.high:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                diff = buf2.ptr[i] - buf1.ptr[i]
                if 0.001 < diff <= self.max_change and self.low <= buf1.ptr[i] <= self.high:
                    result_callback(result_list, i, buf1.ptr[i])

