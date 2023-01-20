from .base_control import BaseControl

class Space(BaseControl):

    def __init__(self, top: int = 0, bottom: int = 0, left: int = 0, right: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.style += "margin: {}px {}px {}px {}px;".format(top, right, bottom, left)

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        return '<div id="{}" style="{}"></div>'.format(self.script_ids[-1], self.style)






