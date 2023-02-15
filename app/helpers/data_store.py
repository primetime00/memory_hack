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


from app.helpers.exceptions import ProcessException
from app.helpers.operation_control import OperationControl


class DataStore(metaclass=SingletonMeta):
    def __init__(self):
        self.process = ""
        self.pid = 0
        self.pids = []
        self.pid_map = {}
        self.open_pids = {}
        self.process_names = []
        self.last_update_time = 0

        self.services = {}

        self.process_classes = []
        self.operation_control = OperationControl()


    def set_service(self, name, service_inst):
        self.services[name] = service_inst

    def get_service(self, name):
        return self.services[name]

    def add_memory_class(self, cls_inst):
        self.process_classes.append(cls_inst)

    def get_process(self, service):
        try:
            return self.services['process'].service_pids[service]['exe']
        except:
            raise ProcessException('Cannot find class')


    def get_last_update_time(self):
        return self.last_update_time

    def get_operation_control(self):
        return self.operation_control

    def kill(self):
        for s_key in self.services.keys():
            self.services[s_key].kill()