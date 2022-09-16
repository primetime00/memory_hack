import time


class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


from app.helpers.memory import Memory
from app.helpers.operation_control import OperationControl
from app.helpers.memory_utils import is_process_valid
import psutil
from threading import Thread
from time import sleep


class DataStore(metaclass=SingletonMeta):
    def __init__(self):
        self.process = ""
        self.pid = 0
        self.process_classes = []
        self.memory = Memory()
        self.operation_control = OperationControl()
        self._process_monitor_thread:Thread = None

    def add_memory_class(self, cls_inst):
        self.process_classes.append(cls_inst)

    def get_process(self):
        return self.process

    def get_memory_handle(self):
        return self.memory.handle

    def get_operation_control(self):
        return self.operation_control

    def set_process(self, p:str):
        if self.memory.handle:
            self.operation_control.control_break()
            for c in self.process_classes:
                c.p_release()
            self.operation_control.clear_control_break()
        if self.memory.handle:
            if psutil.Process(self.memory.handle.pid).status() != 'zombie':
                self.memory.handle.close()
            self.memory.handle = None
        self.pid = 0
        if self._process_monitor_thread and self._process_monitor_thread.is_alive():
            self._process_monitor_thread.join()
        if p.strip():
            self.memory.reset()
            self.memory.handle = self.memory.get_process(p)
            for c in self.process_classes:
                c.p_set(self.memory, p)
        self.process = p
        if self.memory.handle:
            self.pid = self.memory.handle.pid
            self._process_monitor_thread = Thread(target=self._process_monitor)
            self._process_monitor_thread.start()

    def error_process(self):
        if self.memory.handle:
            self.operation_control.control_break()
            for c in self.process_classes:
                c.p_error()
                c.p_release()
            self.operation_control.clear_control_break()
        if self.memory.handle:
            if psutil.Process(self.memory.handle.pid).status() != 'zombie':
                self.memory.handle.close()
            self.memory.handle = None
        self.pid = 0
        self.process = ""


    def _process_monitor(self):
        while self.pid > 0:
            if not is_process_valid(self.pid):
                self.pid = 0
                self.error_process()
            else:
                time.sleep(0.6)


