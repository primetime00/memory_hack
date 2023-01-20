class Build:

    def __init__(self):
        self.built = False

    def perform_build(self, id_map: {}):
        data = self.build(id_map)
        self.built = True
        return data

    def is_built(self):
        return self.built

    def build(self, id_map: {}):
        return None
