from app.script_ui._base import BaseUI

class Text(BaseUI):

    def __init__(self, name: str, title: str, children=None):
        super().__init__(name, title, None, children)

    def ui_data(self, _id):
        return '<span id="{}">{}</span>'.format(_id, self.title)

    def get_text(self):
        return self.title

    def set_text(self, text):
        self.title = text
        self.update_queue.put({'op': "inner-html", 'data': {'html': text}})