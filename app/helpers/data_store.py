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


class DataStore(metaclass=SingletonMeta):
    def __init__(self):
        self.process = ""
        self.process_classes = []
        self.memory = Memory()

    def add_memory_class(self, cls_inst):
        self.process_classes.append(cls_inst)

    def get_process(self):
        return self.process

    def get_memory_handle(self):
        return self.memory.handle

    def set_process(self, p:str):
        if self.memory.handle:
            for c in self.process_classes:
                c.p_release()
        if self.memory.handle:
            self.memory.handle.close()
            self.memory.handle = None
        if p.strip():
            self.memory.reset()
            self.memory.handle = self.memory.get_process(p)
            for c in self.process_classes:
                c.p_set(self.memory, p)
        self.process = p