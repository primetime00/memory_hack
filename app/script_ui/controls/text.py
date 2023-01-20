from .base_control import BaseControl

class Text(BaseControl):

    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def build(self, id_map: {}):
        id_map[self.script_ids[-1]] = self
        return '<div id="{}">{}</div>'.format(self.script_ids[-1], self.text)

    def set_text(self, txt: str):
        self.text = txt
        [self.update_queue.put({'op': "inner-html", 'data': {'html': txt, 'id': x}}) for x in self.script_ids]

    def get_text(self):
        return self.text

    def on_reload(self):
        if self.text is not None:
            self.set_text(self.text)
        super().on_reload()





