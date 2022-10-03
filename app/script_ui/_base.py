from app.script_ui.input import Input


class BaseUI:
    def __init__(self, title, interact_callback, enable_checker=None, input_handler: Input=None):
        self.title = title
        self.id = ""
        self.interact_callback = interact_callback
        self.enable_checker = enable_checker
        self.enabled = False
        self.input_handler = input_handler

    def base_ui_data(self):
        data = self.ui_data()
        if self.input_handler:
            data = self.input_handler.ui_data(self.id) + data
        if data:
            return "<ons-list-item>{}</ons-list-item>".format(data)
        return ""

    def ui_data(self):
        return ""

    def is_enabled(self):
        return self.enabled

    def update_status(self):
        validate = (not self.input_handler) or (self.input_handler and self.input_handler.check_value() is not None)
        enable = (not self.enable_checker) or (self.enable_checker and self.enable_checker())
        self.enabled = (validate and enable)

    def base_handle_interaction(self, data):
        if self.input_handler:
            if self.input_handler.check_interaction(data):
                self.update_status()
                return
        self.handle_interaction(data)

    def handle_interaction(self, data):
        pass

    def get_interact_callback(self):
        return self.interact_callback

    def process(self):
        pass

    def int_callback(self):
        self.get_interact_callback()(self)

    def get_id(self):
        return self.id
