import math

from app.helpers.exceptions import OperationException


class Operation:
    def __init__(self):
        pass

class MemoryOperation(Operation):
    def __init__(self):
        super().__init__()

    def run(self, current_read, previous_read):
        if isinstance(previous_read, bytes):
            return self.operation(current_read,  self.process(previous_read))
        else:
            return self.operation(current_read, previous_read)

    def operation(self, current_read, previous_read):
        pass

    def process(self, read: bytes):
        return 0


class DecreaseOperation(MemoryOperation):
    def operation(self, current_read, previous_read):
        return current_read < previous_read

class IncreaseOperation(MemoryOperation):
    def operation(self, current_read, previous_read):
        return current_read > previous_read

class UnchangedOperation(MemoryOperation):
    def operation(self, current_read, previous_read):
        return current_read == previous_read

class ChangedOperation(UnchangedOperation):
    def operation(self, current_read, previous_read):
        return not super().operation(current_read, previous_read)


class DecreaseOperationFloat(MemoryOperation):
    def operation(self, current_read, previous_read):
        return previous_read - current_read > 0.001

class IncreaseOperationFloat(MemoryOperation):
    def operation(self, current_read, previous_read):
        return current_read - previous_read > 0.001


class UnchangedOperationFloat(MemoryOperation):
    def operation(self, current_read, previous_read):
        return math.isclose(current_read, previous_read, abs_tol=0.001)

class ChangedOperationFloat(UnchangedOperationFloat):
    def operation(self, current_read, previous_read):
        return not super().operation(current_read, previous_read)

class ChangedByOperation(MemoryOperation):
    def __init__(self, delta):
        super().__init__()
        self.delta = delta

    def operation(self, current_read, previous_read):
        return current_read - previous_read == self.delta

class ChangedByOperationFloat(ChangedByOperation):
    def operation(self, current_read, previous_read):
        return math.isclose(current_read - previous_read, self.delta, abs_tol=0.001)


class ValueOperation(Operation):
    def __init__(self, args):
        super().__init__()
        self.user_args = args

    def run(self, current_read):
        return self.operation(current_read)

    def operation(self, current_read):
        return False

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
    def operation(self, current_read):
        return current_read < self.user_args

class GreaterThan(ValueOperation):
    def operation(self, current_read):
        return current_read > self.user_args

class LessThanFloat(ValueOperation):
    def operation(self, current_read):
        return self.user_args - current_read > 0.001

class GreaterThanFloat(ValueOperation):
    def operation(self, current_read):
        return current_read - self.user_args > 0.001


class NotEqualInt(ValueOperation):
    def operation(self, current_read) -> bool:
        return current_read != self.user_args

class EqualInt(NotEqualInt):
    def operation(self, current_read) -> bool:
        return not super().operation(current_read)


class NotEqualArray(ArrayValueOperation):
    def operation(self, current_read) -> bool:
        for i in range(0, len(self.user_args)):
            if i >= len(current_read):
                continue
            if self.user_args[i] > 255:
                continue
            if self.user_args[i] != current_read[i]:
                return True
        return False

class EqualArray(NotEqualArray):
    def operation(self, read) -> bool:
        return not super().operation(read)

class NotEqualFloat(ValueOperation):
    def operation(self, current_read) -> bool:
        return not math.isclose(current_read, self.user_args, abs_tol=0.001)

class EqualFloat(NotEqualFloat):
    def operation(self, current_read) -> bool:
        return not super().operation(current_read)

class Between(ValueOperation):
    def operation(self, current_read) -> bool:
        return self.user_args[0] < current_read < self.user_args[1]

class BetweenFloat(ValueOperation):
    def operation(self, current_read) -> bool:
        return current_read - self.user_args[0] > 0.001 and self.user_args[1] - current_read > 0.001

