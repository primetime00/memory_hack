import mem_edit

from app.helpers.data_store import DataStore

class MemoryHandler:
    def __init__(self, service_name):
        self.process_data = None
        self.service_name = service_name
        self.memory = None
        #add this to the process service

        DataStore().get_service('process').add_process_service(self)

    def get_process_name(self):
        try:
            return self.process_data['name']
        except:
            return ""

    def p_release(self):
        self.process_data = None
        self.release()

    def p_set(self, data):
        self.process_data = data
        self.set(data)

    def mem(self) -> mem_edit.Process:
        if self.process_data and 'process' in self.process_data:
            return self.process_data['process']
        raise IOError()

    def has_mem(self):
        return self.process_data and 'process' in self.process_data

    def p_error(self, msg: str):
        self.process_data = None
        self.process_error(msg)

    def process_error(self, msg: str):
        pass

    def release(self):
        pass

    def set(self, data):
        pass

    def get_service_name(self):
        return self.service_name