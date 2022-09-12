class MemManipException(Exception):
    def __init__(self, msg, from_thread=False):
        self.from_thread = from_thread
        self.msg = msg

    def is_from_thread(self):
        return self.from_thread

    def get_message(self):
        return self.msg