class AOB:
    def __init__(self, name, aob_str):
        self.name = name
        self.aob_string = aob_str
        self.bases = []

    def get_aob_string(self):
        return self.aob_string

    def get_name(self):
        return self.name

    def is_found(self):
        return len(self.bases) > 0

    def get_bases(self):
        return self.bases

    def set_bases(self, base_list):
        self.bases = base_list

    def clear_bases(self):
        self.bases.clear()


