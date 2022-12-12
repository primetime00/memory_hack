import time

class PollTimer:
    def __init__(self, seconds) -> None:
        self.seconds = seconds
        self.now = time.time()

    def start(self):
        self.now = time.time()

    def has_elapsed(self) -> bool:
        el = time.time() - self.now
        if el >= self.seconds:
            self.now = time.time()
            return True
        return False
