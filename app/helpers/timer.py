import time
from threading import Thread, Event


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

class ThreadTimer(Thread):
    def __init__(self, seconds:int, func: callable, *args):
        super().__init__(target=self.run)
        self.event = Event()
        self.cf = func
        self.seconds = seconds
        self.args = args
        self.start()

    def run(self):
        while not self.event.is_set():
            self.event.wait(self.seconds)
            if not self.event.is_set():
                self.cf(self.args)

    def stop(self):
        self.event.set()
        self.join()
