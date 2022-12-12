from queue import Queue

class BaseUI:
    def __init__(self, name:str, title:str, enable_checker: callable = None, children=None):
        self.name = name
        self.title = title
        self.parent = None
        self.id = ""
        self.enable_checker = enable_checker
        self.enabled = False
        self.on_enabled = None
        self.on_hidden = None
        self.on_process = None

        self.interact_queue = Queue()
        self.update_queue = Queue()

        if children:
            for c in children:
                c.parent = self
        self.children = children

        self.updated = False
        self.return_data = None

    def get_name(self):
        return self.name
    def set_enable_check(self, func: callable):
        self.enable_checker = func
    def set_on_enabled(self, func: callable):
        self.on_enabled = func

    def set_on_hidden(self, func: callable):
        self.on_hidden = func

    def set_on_process(self, func: callable):
        self.on_process = func

    def get_return_data(self):
        return self.return_data

    def add_instruction(self, function, args=()):
        self.interact_queue.put((function, args))

    def disable(self):
        self.update_queue.put({'op': "add_attribute", 'data': {'attr': 'disabled', 'value': 'disabled'}})
        self.enabled = False
        if self.on_enabled:
            self.on_enabled(self, False)

    def enable(self):
        self.update_queue.put({'op': "remove_attribute", 'data': {'attr': 'disabled'}})
        self.enabled = True
        if self.on_enabled:
            self.on_enabled(self, True)

    def hide(self):
        self.update_queue.put({'op': "script", 'data': {'script': '$("#{}").parent().hide();'.format(self.id)}})
        if self.on_hidden:
            self.on_hidden(self, True)


    def show(self):
        self.update_queue.put({'op': "script", 'data': {'script': '$("#{}").parent().show();'.format(self.id)}})
        if self.on_hidden:
            self.on_hidden(self, False)

    def inner(self, html):
        self.update_queue.put({'op': "inner-html", 'data': {'html': html}})

    def base_ui_data(self):
        data = self.ui_data(str(self.id))
        if self.children:
            for c in self.children:
                data = data+c.base_ui_data()
        if data and not self.parent:
            return "<ons-list-item>{}</ons-list-item>".format(data)
        return data

    def ui_data(self, _id):
        return ""

    def is_enabled(self):
        return self.enabled

    def base_handle_interaction(self, data):
        self.handle_interaction(data)

    def handle_interaction(self, data):
        pass

    def base_process(self):
        if self.children:
            for c in self.children:
                c.base_process()
        self.update()
        self.process()

    def process(self):
        if self.enable_checker:
            if not self.enable_checker():
                if self.is_enabled():
                    self.disable()
                return
            else:
                if not self.is_enabled():
                    self.enable()
        while not self.interact_queue.empty():
            func, args = self.interact_queue.get()
            func(self, *args)
        if self.on_process:
            self.on_process(self)


    def update(self):
        pass

    def get_id(self):
        return self.id
