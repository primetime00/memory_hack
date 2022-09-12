import time
from app.helpers.exceptions import ProgressException

class Progress:
    def __init__(self, _min=0, _max=100, _lapse=0.5):
        self.min = _min
        self.max = _max
        self.current_progress = 0
        self.lapse = _lapse
        self.last_time = -1
        self.constraints = []
        self.current_constraint = -1

    def set_max(self, _max):
        self.max = _max

    def set_min(self, _min):
        self.min = _min

    def add_constraint(self, _min, _max, pc: float):
        self.constraints.append({'min': _min, 'max': _max, 'pc': pc})
        if self.current_constraint < 0:
            self.current_constraint = 0

    def increment(self, inc):
        if self.last_time == -1:
            self.update(inc)
        else:
            now = time.time()
            if now-self.last_time > self.lapse:
                self.update(inc)

    def get_progress(self):
        return round(self.current_progress, 2) * 100

    def update(self, inc):
        if self.current_constraint < 0:
            self.current_progress = float(inc) / self.max
        else:
            if self.current_constraint  >= len(self.constraints):
                raise ProgressException('Tried to update constrain that does not exist')
            pcs = sum([x['pc'] for x in self.constraints[0:self.current_constraint]])
            current = (float(inc) / self.constraints[self.current_constraint]['max']) * self.constraints[self.current_constraint]['pc']
            self.current_progress = pcs + current
        self.last_time = time.time()

    def mark(self):
        if self.current_constraint < 0:
            self.current_progress = 1
        else:
            pcs = sum([x['pc'] for x in self.constraints[0:self.current_constraint]])
            current = self.constraints[self.current_constraint]['pc']
            self.current_progress = pcs + current
            self.current_constraint += 1



