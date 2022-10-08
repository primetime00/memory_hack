from app.helpers.mem_manip_exception import MemManipException

class SearchException(MemManipException):
    pass

class ScriptException(MemManipException):
    pass

class AOBException(MemManipException):
    pass

class ProgressException(MemManipException):
    pass

class CodelistException(MemManipException):
    pass

class ProcessException(MemManipException):
    pass
class BreakException(MemManipException):
    def __init__(self):
        super().__init__("Operation Break", True)
