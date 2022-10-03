from app.helpers.aob_value import AOBValue
class AOB:
    def __init__(self, name, aob_str):
        self.name = name
        self.aob = AOBValue(aob_str)
        self.aob_string = aob_str
        self.bases = []
        self._last_found = -1

    def get_aob_string(self):
        return self.aob.aob_item['aob_string']

    def get_name(self):
        return self.name

    def is_found(self):
        return len(self.bases) > 0

    def get_bases(self):
        return self.bases

    def set_bases(self, base_list):
        self.bases = base_list
        self._last_found = len(base_list)

    def clear_bases(self):
        self.bases.clear()
        self._last_found = 0

    def will_warn(self):
        return self._last_found != 0



