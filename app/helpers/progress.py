class Progress:
    def __init__(self, _min=0, _max=100):
        self.min = _min
        self.max = _max
        self.current_count = 0
        self.current_progress = 0
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
        self.current_count += inc

    def set(self, val):
        self.current_count = val

    def get_progress(self):
        self.update()
        return round(self.current_progress*100)

    def update(self):
        if self.current_constraint < 0:
            self.current_progress = float(self.current_count) / self.max
        else:
            if self.current_constraint >= len(self.constraints):
                pcs = sum([x['pc'] for x in self.constraints[0:len(self.constraints)]])
                self.current_progress = pcs
            else:
                pcs = sum([x['pc'] for x in self.constraints[0:self.current_constraint]])
                normalized = (self.current_count - self.constraints[self.current_constraint]['min']) / (self.constraints[self.current_constraint]['max'] - self.constraints[self.current_constraint]['min'])
                current = normalized * self.constraints[self.current_constraint]['pc']
                self.current_progress = pcs + current

    def mark(self):
        self.current_count = 0
        if self.current_constraint < 0:
            self.current_progress = 1
        else:
            pcs = sum([x['pc'] for x in self.constraints[0:self.current_constraint]])
            current = self.constraints[self.current_constraint]['pc']
            self.current_progress = pcs + current
            self.current_constraint += 1

    def reset(self):
        self.min = 0
        self.max = 100
        self.current_count = 0
        self.current_progress = 0
        self.constraints = []
        self.current_constraint = -1




