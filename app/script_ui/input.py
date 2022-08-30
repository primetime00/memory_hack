class Input:

    def __init__(self, validation_checker=None, default_value="1000"):
        self.validation_checker = validation_checker
        self.input_value = default_value
        self.validated_value = None

    def ui_data(self, id: str):
        return '<ons-input id="input_{}" modifier="underbar" placeholder="{}" onchange="script.script_interact_value(event)" float></ons-input>'.format(id, self.input_value)

    def get_value(self):
        return self.input_value

    def get_validated_value(self):
        return self.validated_value

    def has_validated_value(self):
        return self.validated_value is not None

    def check_interaction(self, data):
        if 'value' in data:
            self.input_value = data['value']
            return True
        return False

    def check_value(self):
        if self.validation_checker:
            self.validated_value = self.validation_checker(self.input_value)
        elif self.input_value.isdigit():
            self.validated_value = int(self.input_value)
        else:
            self.validated_value = None
        return self.validated_value