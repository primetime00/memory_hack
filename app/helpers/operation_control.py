class OperationControl:
    def __init__(self):
        self._control_break = False

    def control_break(self):
        self._control_break = True

    def clear_control_break(self):
        self._control_break = False

    def is_control_break(self):
        return self._control_break
