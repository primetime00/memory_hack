import app.helpers.process_utils as pu
from app.helpers.data_store import DataStore

class DynamicHTML:
    def __init__(self, filename, cnt):
        self.filename = filename
        self.result_html = ""
        self.count = cnt
        self.process()

    def get_html(self):
        return self.result_html

    def process(self):
        with open(self.filename, 'rt') as ac:
            data = ac.read()
        if '##process_control##' in data:
            data = self.process_control(data)
        self.result_html = data

    def process_control(self, data):
        options = ""
        procs = list(reversed([k for k, v in pu.get_process_list().items()]))
        current_process = DataStore().get_process()
        if current_process and current_process not in procs:
            procs.insert(0, current_process)
        options += '<option value="{}">{}</option>'.format('_null', '')
        for s in procs:
            options += '<option value="{}">{}</option>'.format(s, s)
        with open('resources/process_control.html', 'rt') as ac:
            pctrl = ac.read().replace("##processes##", options)+'\n'
        return data.replace('##process_control##', pctrl).replace("%process%", "process_{}".format(self.count))
