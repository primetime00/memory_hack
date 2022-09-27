import abc

class Service(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self):
        pass


    @abc.abstractmethod
    def kill(self):
        return

