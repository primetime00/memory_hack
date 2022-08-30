from app.helpers.data_store import DataStore

class MemoryHandler:
    def __init__(self):
        self.memory = None
        DataStore().add_memory_class(self)

    def p_release(self):
        self.release()

    def p_set(self, memory, process):
        self.memory = memory
        self.set(memory, process)

    def release(self):
        pass

    def set(self, handler, process):
        pass

    def get_memory(self):
        return self.memory