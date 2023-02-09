from app.helpers.memory_hack_exception import MemoryHackException

class SearchException(MemoryHackException):
    pass

class ScriptException(MemoryHackException):
    pass

class AOBException(MemoryHackException):
    pass

class ProgressException(MemoryHackException):
    pass

class CodelistException(MemoryHackException):
    pass

class ProcessException(MemoryHackException):
    pass
class BreakException(MemoryHackException):
    def __init__(self):
        super().__init__("Operation Break", True)

class ValueException(MemoryHackException):
    pass

class BufferException(MemoryHackException):
    pass

class OperationException(MemoryHackException):
    pass
