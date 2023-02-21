import ctypes
import json
from struct import unpack
from typing import cast

from app.script_ui import controls


class AOBResultControl(controls.Group):
    def __init__(self, on_copy: callable, on_count: callable, **kwargs):
        super().__init__(**kwargs)
        self.max_rows = 10
        self.addresses = []
        self.aob = ''
        self.aob_bytes = []
        self.current_aob_bytes: dict[int, list] = {}
        self.stats: dict[int, dict] = {}
        self.build_ui()
        self.on_copy = on_copy
        self.on_count = on_count
        self.html_data = ""
        self.offset = ""

    def build_ui(self):
        row_1: controls.Row = cast(controls.Row, self.add_element(controls.Row(id="AOB_RESULT_ROW")))

    def generate(self):
        self.html_data = ''
        for row_index in range(0, min(len(self.addresses), self.max_rows)):
            self.html_data += '<ons-row data-aobi_address={}>\n'.format(self.addresses[row_index])
            cp_button = '<ons-button id="{}_aobi_copybutton-{:03}" modifier="quiet" data-aobi_address_cp="{}"onclick="script.script_interact_button(event)"><ons-icon icon="md-copy" size="15px"></ons-icon></ons-button>'.format(self.script_ids[-1], row_index, self.addresses[row_index])
            self.html_data += '<ons-row><ons-col align="center" class="col ons-col-inner" width="40%">Address:</ons-col><ons-col align="center" class="col ons-col-inner aobi-address" width="50%">{:X}</ons-col><ons-col align="center" class="col ons-col-inner aobi-address" width="10%">{}</ons-col></ons-row>\n'.format(self.addresses[row_index], cp_button)
            self.html_data += '<ons-row><ons-col align="center" class="col ons-col-inner" width="40%">Changes:</ons-col><ons-col align="center" class="col ons-col-inner aobi-changes" width="60%">5</ons-col></ons-row>\n'
            self.html_data += '<ons-row><ons-col align="center" class="col ons-col-inner" width="40%">Wildcards:</ons-col><ons-col align="center" class="col ons-col-inner aobi-wildcards" width="60%">5</ons-col></ons-row>\n'
            self.html_data += '<ons-row><ons-col align="center" class="col ons-col-inner" width="40%">Longest Wildcard Run:</ons-col><ons-col align="center" class="col ons-col-inner aobi-run" width="60%">5</ons-col></ons-row>\n'
            self.html_data += '<ons-row><ons-col align="center" class="col ons-col-inner" width="40%"><ons-button modifier="quiet" id="{}_aobi_countbutton-{:03}" class="memory_button" style="background:none; border:none;" data-aobi_address="{}" onclick="script.script_interact_button(event)">Count</ons-button></ons-col><ons-col align="center" class="col ons-col-inner aobi-count" width="60%"></ons-col></ons-row>\n'.format(self.script_ids[-1], row_index, self.addresses[row_index])
            self.html_data += '</ons-row>\n'
        return self.html_data


    def on_copy(self, name, ele_id, data):
        res = self.get_element("OUTPUT_ADDRESS_STRING").get_text()
        cast(controls.advanced.CopyButton, self.get_element("COPY_BUTTON")).copy({'address': res})


    def handle_interaction(self, _id, data):
        if 'aobi_countbutton' in _id:
            base = data['data']['aobi_address']
            str = " ".join(['{:02X}'.format(x) if x < 256 else '??' for x in self.current_aob_bytes[base]])
            num = self.on_count(base, str)
            js = 'var _row = $("[data-aobi_address=\'{}\']");'.format(base)
            js += '_row.find(".aobi-count").html("{}");'.format(num)
            self.js(js)
        elif 'aobi_copybutton' in _id:
            base = data['data']['aobi_address_cp']
            aob = " ".join(['{:02X}'.format(x) if x < 256 else '??' for x in self.current_aob_bytes[base]])
            offset = self.offset
            self.js('document.clipboard.copy({})'.format(json.dumps({'aob': aob, 'offset': offset})))

    def set_aob(self, aob: str, offset:str, addresses: list):
        self.aob = aob
        self.offset = offset
        self.aob_bytes.clear()
        for aob in self.aob.split(' '):
            if aob == '??':
                self.aob_bytes.append(256)
            else:
                self.aob_bytes.append(int(aob, 16))
        wildcards = len([x for x in self.aob_bytes if x >= 256])
        for addr in addresses:
            self.current_aob_bytes[addr] = self.aob_bytes.copy()
            self.stats[addr] = {'wildcards': wildcards}
        self.addresses = addresses
        self.get_element("AOB_RESULT_ROW").inner(self.generate())


    def set_read(self, data:bytes, base: int):
        for i in range(0, len(data)):
            if self.current_aob_bytes[base][i] == 256:
                continue
            if data[i] == self.current_aob_bytes[base][i]:
                continue
            self.current_aob_bytes[base][i] = 256
        #count the changes / wildcards
        count = 0
        wildcards = 0
        consecutive_wildcards = -1
        wildcard_run = -1
        for i in range(0, len(self.current_aob_bytes[base])):
            if self.current_aob_bytes[base][i] != self.aob_bytes[i]:
                count += 1
            if self.current_aob_bytes[base][i] >= 256 > self.aob_bytes[i]:
                wildcards += 1
            if self.current_aob_bytes[base][i] >= 256:
                if wildcard_run < 0:
                    wildcard_run = 1
                else:
                    wildcard_run += 1
            if self.current_aob_bytes[base][i] < 256 and wildcard_run >= 1:
                consecutive_wildcards = max(wildcard_run, consecutive_wildcards)
                wildcard_run = -1

        self.stats[base]["diff"] = count
        self.stats[base]["wildcard_diff"] = wildcards
        self.stats[base]["max_wildcard_runs"] = consecutive_wildcards

        js = 'var _row = $("[data-aobi_address=\'{}\']");'.format(base)
        js += '_row.find(".aobi-changes").html("{}");'.format(self.stats[base]["diff"])
        js += '_row.find(".aobi-wildcards").html("{}/{}");'.format(self.stats[base]["wildcards"], self.stats[base]["wildcard_diff"])
        js += '_row.find(".aobi-run").html("{}");'.format(self.stats[base]["max_wildcard_runs"])
        self.js(js)




