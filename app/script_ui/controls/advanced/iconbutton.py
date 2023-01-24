import json

from ..button import Button


class IconButton(Button):

    def __init__(self, icon: str, on_click: callable, quiet: bool = True, **kwargs):
        super().__init__("", on_click, quiet, **kwargs)
        size = kwargs.get('size', 20)
        self.text = '<ons-icon icon="{}" size="{}px"></ons-icon>'.format(icon, size)


class CopyButton(IconButton):
    def __init__(self, on_click: callable, **kwargs):
        kwargs['width'] = "50px"
        super().__init__("md-copy", on_click, True, **kwargs)

    def copy(self, data: dict):
        data_str = json.dumps(data)
        self.update_queue.put({'op': "script", 'data': {'script': 'document.clipboard.copy({})'.format(data_str)}})

class PasteButton(IconButton):
    def __init__(self, on_click: callable, **kwargs):
        kwargs['width'] = "50px"
        super().__init__("md-paste", on_click, True, **kwargs)




