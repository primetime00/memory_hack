from app.helpers.exceptions import OperationException


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

    def run(self, buf_ptr1, buf_ptr2, adjusted_length: int, result_callback: callable, result_list: list):
        pass


class DecreaseOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] < current_and_previous_read[1]

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_current_ptr[i] < buf_previous_ptr[i]:
                result_callback(result_list, i, buf_current_ptr[i])


class IncreaseOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] > current_and_previous_read[1]

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_current_ptr[i] > buf_previous_ptr[i]:
                result_callback(result_list, i, buf_current_ptr[i])


class UnchangedOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] == current_and_previous_read[1]

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_current_ptr[i] == buf_previous_ptr[i]:
                result_callback(result_list, i, buf_current_ptr[i])


class ChangedOperation(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] != current_and_previous_read[1]

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_current_ptr[i] != buf_previous_ptr[i]:
                result_callback(result_list, i, buf_current_ptr[i])



class DecreaseOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[1] - current_and_previous_read[0] > 0.001

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_previous_ptr[i] - buf_current_ptr[i] > 0.001:
                result_callback(result_list, i, buf_current_ptr[i])


class IncreaseOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] - current_and_previous_read[1] > 0.001

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_current_ptr[i] - buf_previous_ptr[i] > 0.001:
                result_callback(result_list, i, buf_current_ptr[i])


class UnchangedOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return -0.001 < current_and_previous_read[0] - current_and_previous_read[1] < 0.001

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if -0.001 < buf_current_ptr[i] - buf_previous_ptr[i] < 0.001:
                result_callback(result_list, i, buf_current_ptr[i])

class ChangedOperationFloat(MemoryOperation):
    def operation(self, *current_and_previous_read):
        return not (-0.001 < current_and_previous_read[0] - current_and_previous_read[1] < 0.001)


    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if not (-0.001 < buf_current_ptr[i] - buf_previous_ptr[i] < 0.001):
                result_callback(result_list, i, buf_current_ptr[i])


class ChangedByOperation(MemoryOperation):
    def __init__(self, delta):
        super().__init__()
        self.delta = delta

    def operation(self, *current_and_previous_read):
        return current_and_previous_read[0] - current_and_previous_read[1] == self.delta

    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if buf_current_ptr[i] - buf_previous_ptr[i] == self.delta:
                result_callback(result_list, i, buf_current_ptr[i])

class ChangedByOperationFloat(ChangedByOperation):
    def operation(self, *current_and_previous_read):
        return -0.001 <= (current_and_previous_read[0] - current_and_previous_read[1]) - self.delta <= 0.001


    def run(self, buf_current_ptr, buf_previous_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            if -0.001 <= (buf_current_ptr[i] - buf_previous_ptr[i]) - self.delta <= 0.001:
                result_callback(result_list, i, buf_current_ptr[i])



class ValueOperation(Operation):
    def __init__(self, args):
        super().__init__()
        self.user_args = args

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
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

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if read < self.user_args:
                result_callback(result_list, i, read)

class GreaterThan(ValueOperation):
    def operation(self, *current_read):
        return current_read[0] > self.user_args

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if read > self.user_args:
                result_callback(result_list, i, read)

class LessThanFloat(ValueOperation):
    def operation(self, *current_read):
        return self.user_args - current_read[0] > 0.001

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if self.user_args - read > 0.001:
                result_callback(result_list, i, read)

class GreaterThanFloat(ValueOperation):
    def operation(self, *current_read):
        return current_read[0] - self.user_args > 0.001

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if read - self.user_args > 0.001:
                result_callback(result_list, i, read)



class NotEqualInt(ValueOperation):
    def operation(self, *current_read) -> bool:
        return current_read[0] != self.user_args

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if read != self.user_args:
                result_callback(result_list, i, read)

class EqualInt(ValueOperation):
    def operation(self, *current_read) -> bool:
        return current_read[0] == self.user_args

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
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

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        u_len = len(self.user_args)
        i = 0
        while i < adjusted_length-u_len:
            read = buf_ptr[i:i+u_len]
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

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        u_len = len(self.user_args)
        i = 0
        while i < adjusted_length-u_len:
            read = buf_ptr[i:i+u_len]
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

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if not (-0.001 < self.user_args - read < 0.001):
                result_callback(result_list, i, read)


class EqualFloat(NotEqualFloat):
    def operation(self, *current_read) -> bool:
        return -0.001 < self.user_args - current_read[0] < 0.001

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if -0.001 < self.user_args - read < 0.001:
                result_callback(result_list, i, read)


class Between(ValueOperation):
    def operation(self, *current_read) -> bool:
        return self.user_args[0] < current_read[0] < self.user_args[1]

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if self.user_args[0] < read < self.user_args[1]:
                result_callback(result_list, i, read)



class BetweenFloat(ValueOperation):
    def operation(self, *current_read) -> bool:
        return self.user_args[0] < current_read[0] < self.user_args[1]

    def run(self, buf_ptr, adjusted_length: int, result_callback: callable, result_list: list):
        for i in range(0, adjusted_length):
            read = buf_ptr[i]
            if self.user_args[0] < read < self.user_args[1]:
                result_callback(result_list, i, read)

