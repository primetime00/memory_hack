import ctypes
from typing import TYPE_CHECKING, Union

from app.helpers.exceptions import OperationException

if TYPE_CHECKING:
    from app.search.buffer import SearchBuffer

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]


class Operation:
    def __init__(self):
        pass

    def operation(self, *current_read) -> bool:
        return False

class MemoryOperation(Operation):
    def __init__(self):
        super().__init__()

    def operation(self, *current_read) -> bool:
        return super().operation(*current_read)

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        pass

class DecreaseOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] < current_and_previous_read[1]

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r1 < r2:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf1.ptr[i] < buf2.ptr[i]:
                    result_callback(result_list, i, buf1.ptr[i])

class IncreaseOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] > current_and_previous_read[1]
    
    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r1 > r2:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf1.ptr[i] > buf2.ptr[i]:
                    result_callback(result_list, i, buf1.ptr[i])

class UnchangedOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] == current_and_previous_read[1]

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r1 == r2:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf1.ptr[i] == buf2.ptr[i]:
                    result_callback(result_list, i, buf1.ptr[i])

class ChangedOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] != current_and_previous_read[1]

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r1 != r2:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf1.ptr[i] != buf2.ptr[i]:
                    result_callback(result_list, i, buf1.ptr[i])



class DecreaseOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[1] - current_and_previous_read[0] > 0.001
    
    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r2 - r1 > 0.001:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf2.ptr[i] - buf1.ptr[i] > 0.001:
                    result_callback(result_list, i, buf1.ptr[i])

class IncreaseOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] - current_and_previous_read[1] > 0.001

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r1 - r2 > 0.001:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf1.ptr[i] - buf2.ptr[i] > 0.001:
                    result_callback(result_list, i, buf1.ptr[i])

class UnchangedOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return -0.001 < current_and_previous_read[0] - current_and_previous_read[1] < 0.001

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if -0.001 < r1 - r2 < 0.001:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if -0.001 < buf1.ptr[i] - buf2.ptr[i] < 0.001:
                    result_callback(result_list, i, buf1.ptr[i])


class ChangedOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return not (-0.001 < current_and_previous_read[0] - current_and_previous_read[1] < 0.001)

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if not(-0.001 < r1 - r2 < 0.001):
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if not(-0.001 < buf1.ptr[i] - buf2.ptr[i] < 0.001):
                    result_callback(result_list, i, buf1.ptr[i])
                    
class ChangedByOperation(MemoryOperation):
    def __init__(self, delta):
        super().__init__()
        self.delta = delta

    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] - current_and_previous_read[1] == self.delta

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if r1 - r2 == self.delta:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if buf1.ptr[i] - buf2.ptr[i] == self.delta:
                    result_callback(result_list, i, buf1.ptr[i])


class ChangedByOperationFloat(ChangedByOperation):
    def operation(self, *current_and_previous_read):
        return -0.001 <= (current_and_previous_read[0] - current_and_previous_read[1]) - self.delta <= 0.001

    def run(self, buf1: "SearchBuffer", buf2: "SearchBuffer", result_callback: callable, result_list: list):
        length = min(len(buf1), len(buf2))
        if not buf1.aligned:
            address1 = ctypes.addressof(buf1.buffer)
            address2 = ctypes.addressof(buf2.buffer)
            length = min(len(buf1.buffer), len(buf2.buffer)) - ctypes.sizeof(buf1.store_type)-1
            for i in range(0, length):
                r1 = buf1.store_type.from_address(address1+i).value
                r2 = buf1.store_type.from_address(address2+i).value
                if -0.001 <= (r1 - r2) - self.delta <= 0.001:
                    result_callback(result_list, i, r1)
        else:
            for i in range(0, length):
                if -0.001 <= (buf1.ptr[i] - buf2.ptr[i]) - self.delta <= 0.001:
                    result_callback(result_list, i, buf1.ptr[i])

class ValueOperation(Operation):
    def __init__(self, args):
        super().__init__()
        self.user_args = args

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        pass

class ArrayValueOperation(ValueOperation):
    def __init__(self, args):
        from app.helpers.aob_value import AOBValue
        super().__init__(args)
        if type(args) is bytes:
            self.user_args = [args[i] for i in range(0, len(args))]
        elif type(args) is str:
            v = AOBValue(args)
            self.user_args = v.aob_item['aob_bytes']
        elif type(args) is not list:
            raise OperationException("Array previous read is unknown.")

class LessThan(ValueOperation):
    def operation(self, *current_read):
        return current_read[0] < self.user_args

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if read < self.user_args:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if read < self.user_args:
                    result_callback(result_list, i, read)

class GreaterThan(ValueOperation):
    def operation(self, *current_read):
        return current_read[0] > self.user_args

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if read > self.user_args:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if read > self.user_args:
                    result_callback(result_list, i, read)

class LessThanFloat(ValueOperation):
    def operation(self, *current_read):
        return self.user_args - current_read[0] > 0.001

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if self.user_args - read > 0.001:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if self.user_args - read > 0.001:
                    result_callback(result_list, i, read)

class GreaterThanFloat(ValueOperation):
    def operation(self, *current_read):
        return current_read[0] - self.user_args > 0.001

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if read - self.user_args > 0.001:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if read - self.user_args > 0.001:
                    result_callback(result_list, i, read)


class NotEqualInt(ValueOperation):
    def operation(self, *current_read) -> bool:
        return current_read[0] != self.user_args

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if read != self.user_args:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if read != self.user_args:
                    result_callback(result_list, i, read)

class EqualInt(ValueOperation):
    def operation(self, *current_read) -> bool:
        return current_read[0] == self.user_args

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if read == self.user_args:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if read == self.user_args:
                    result_callback(result_list, i, read)

class NotEqualArray(ArrayValueOperation):
    def operation(self, *current_read) -> bool:
        for i in range(0, len(self.user_args)):
            if i >= len(current_read[0]):
                continue
            if self.user_args[i] > 255:
                continue
            if self.user_args[i] != current_read[0][i]:
                return True
        return False

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        u_len = len(self.user_args)
        length = len(buffer)
        i = 0
        while i < length-u_len:
            read = buffer.ptr[i:i+u_len]
            i += 1
            for j in range(0, len(self.user_args)):
                if self.user_args[j] > 255:
                    continue
                if self.user_args[j] != read[j]:
                    result_callback(result_list, i-1, read)
                    i += j
                    break

class EqualArray(NotEqualArray):
    def operation(self, *current_read) -> bool:
        for i in range(0, len(self.user_args)):
            if i >= len(current_read[0]):
                continue
            if self.user_args[i] > 255:
                continue
            if self.user_args[i] != current_read[0][i]:
                return False
        return True

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        u_len = len(self.user_args)
        length = len(buffer)
        i = 0
        while i < length-u_len:
            read = buffer.ptr[i:i+u_len]
            i += 1
            found = True
            for j in range(0, len(self.user_args)):
                if self.user_args[j] > 255:
                    continue
                if self.user_args[j] != read[j]:
                    i += j
                    found = False
                    break
            if found:
                i += u_len-1
                result_callback(result_list, i, read)

class NotEqualFloat(ValueOperation):
    def operation(self, *current_read) -> bool:
        return not (-0.001 < self.user_args - current_read[0] < 0.001)

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if not (-0.001 < self.user_args - read < 0.001):
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if not (-0.001 < self.user_args - read < 0.001):
                    result_callback(result_list, i, read)

class EqualFloat(NotEqualFloat):
    def operation(self, *current_read) -> bool:
        return -0.001 < self.user_args - current_read[0] < 0.001

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if -0.001 < self.user_args - read < 0.001:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if -0.001 < self.user_args - read < 0.001:
                    result_callback(result_list, i, read)

class Between(ValueOperation):
    def operation(self, *current_read) -> bool:
        return self.user_args[0] < current_read[0] < self.user_args[1]

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if self.user_args[0] < read < self.user_args[1]:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if self.user_args[0] < read < self.user_args[1]:
                    result_callback(result_list, i, read)

class BetweenFloat(ValueOperation):
    def operation(self, *current_read) -> bool:
        return self.user_args[0] < current_read[0] < self.user_args[1]

    def run(self, buffer: "SearchBuffer", result_callback: callable, result_list: list):
        length = len(buffer)
        if not buffer.aligned:
            address = ctypes.addressof(buffer.buffer)
            length = len(buffer.buffer) - ctypes.sizeof(buffer.store_type)-1
            for i in range(0, length):
                read = buffer.store_type.from_address(address+i).value
                if self.user_args[0] < read < self.user_args[1]:
                    result_callback(result_list, i, read)
        else:
            for i in range(0, length):
                read = buffer.ptr[i]
                if self.user_args[0] < read < self.user_args[1]:
                    result_callback(result_list, i, read)