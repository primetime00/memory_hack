import ctypes
from struct import unpack
from typing import cast

from app.script_ui import controls


class MemoryControl(controls.Group):
    def __init__(self, on_copy:callable, on_write:callable, on_direction: callable, **kwargs):
        super().__init__(**kwargs)
        self.start_address = 0
        self.memory_buffer: bytes = None
        self.max_rows = 12
        self.max_cols = 10 #120 bytes?
        self.build_ui()
        self.on_copy = on_copy
        self.current_selected_address = -1
        self.last_start_address = -2
        self.html_data = ""
        self.on_write = on_write
        self.on_direction = on_direction

        self.ctrl_map = {
            'OUTPUT_BYTE_1_SIGNED': {'pack': 'b',  'type': ctypes.c_int8, 'size': 1, 'min': -2**(8*1-1), 'max': 2**(8*1-1)-1},
            'OUTPUT_BYTE_1_UNSIGNED': {'pack': 'B', 'type': ctypes.c_uint8, 'size': 1, 'min': 0, 'max': (2**(8*1))-1},
            'OUTPUT_BYTE_2_SIGNED': {'pack': 'h', 'type': ctypes.c_int16, 'size': 2, 'min': -2**(16*1-1), 'max': 2**(16*1-1)-1},
            'OUTPUT_BYTE_2_UNSIGNED': {'pack': 'H', 'type': ctypes.c_uint16, 'size': 2, 'min': 0, 'max': (2**(16*1))-1},
            'OUTPUT_BYTE_4_SIGNED': {'pack': 'i', 'type': ctypes.c_int32, 'size': 4, 'min': -2**(32*1-1), 'max': 2**(32*1-1)-1},
            'OUTPUT_BYTE_4_UNSIGNED': {'pack': 'I', 'type': ctypes.c_uint32, 'size': 4, 'min': 0, 'max': (2**(32*1))-1},
            'OUTPUT_BYTE_8_SIGNED': {'pack': 'q', 'type': ctypes.c_int64, 'size': 8, 'min': -2**(64*1-1), 'max': 2**(64*1-1)-1},
            'OUTPUT_BYTE_8_UNSIGNED': {'pack': 'Q', 'type': ctypes.c_uint64, 'size': 8, 'min': 0, 'max': (2**(64*1))-1},
            'OUTPUT_FLOAT': {'pack': 'f', 'type': ctypes.c_float, 'size': 4, 'min': -9999999.0, 'max': 9999999.0},
        }
        self.ctrl_keys = ['OUTPUT_BYTE_1_SIGNED', 'OUTPUT_BYTE_1_UNSIGNED', 'OUTPUT_BYTE_2_SIGNED', 'OUTPUT_BYTE_2_UNSIGNED', 'OUTPUT_BYTE_4_SIGNED', 'OUTPUT_BYTE_4_UNSIGNED', 'OUTPUT_BYTE_8_SIGNED', 'OUTPUT_BYTE_8_UNSIGNED', 'OUTPUT_FLOAT', ]

    def build_ui(self):
        row_up: controls.Row = cast(controls.Row, self.add_element(controls.Row(id="UP_ROW")))
        row_1: controls.Row = cast(controls.Row, self.add_element(controls.Row(id="MEMORY_ROW")))
        row_dn: controls.Row = cast(controls.Row, self.add_element(controls.Row(id="DOWN_ROW")))
        row_2: controls.Row = cast(controls.Row, self.add_element(controls.Row(id="ADDRESS_ROW")))
        row_3: controls.Row = cast(controls.Row, self.add_element(controls.Row()))
        row_4: controls.Row = cast(controls.Row, self.add_element(controls.Row()))
        row_5: controls.Row = cast(controls.Row, self.add_element(controls.Row()))
        row_6: controls.Row = cast(controls.Row, self.add_element(controls.Row()))
        row_7: controls.Row = cast(controls.Row, self.add_element(controls.Row()))
        row_8: controls.Row = cast(controls.Row, self.add_element(controls.Row()))

        row_up.add_elements([controls.advanced.IconButton('md-chevron-up', self.direction_pressed, True, width='100%', center=True, custom_data=['direction', 'up'])])
        row_dn.add_elements([controls.advanced.IconButton('md-chevron-down', self.direction_pressed, True, width='100%', center=True, custom_data=['direction', 'down'])])

        row_2.add_elements([controls.Text("Address:", width="70px"),
                            controls.Input(on_change=None, id='OUTPUT_ADDRESS_STRING', trigger_by_focus=False, readonly=True),
                            controls.advanced.CopyButton(on_click=self.on_copy, id='COPY_BUTTON'),
                            ])
        row_3.add_elements([
            controls.Space(width="15%"),
            controls.Text("Signed", width="38%"),
            controls.Text("Unsigned", width="38%"),
        ])
        row_4.add_elements([
            controls.Text("Byte", width="15%"),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_1_SIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_1_UNSIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
        ])
        row_5.add_elements([
            controls.Text("2 Bytes", width="15%"),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_2_SIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_2_UNSIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
        ])
        row_6.add_elements([
            controls.Text("4 Bytes", width="15%"),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_4_SIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_4_UNSIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
        ])
        row_7.add_elements([
            controls.Text("8 Bytes", width="15%"),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_8_SIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
            controls.Input(on_change=self.value_changed, width="38%", id='OUTPUT_BYTE_8_UNSIGNED', select_all=True, trigger_by_focus=True, input_mode='decimal'),
        ])
        row_8.add_elements([
            controls.Text("Float", width="15%"),
            controls.Input(on_change=self.value_changed, width="80%", id='OUTPUT_FLOAT', select_all=True, trigger_by_focus=True, input_mode='decimal'),
        ])


    def generate(self):
        self.html_data = ''
        for row_index in range(0, self.max_rows):
            self.html_data += '<ons-row>\n'
            for col_index in range(0, self.max_cols):
                index = self.max_cols*row_index+col_index
                if index < len(self.memory_buffer):
                    self.html_data += '<ons-col align="center" class="col ons-col-inner">'
                    self.html_data += '<button id="{}_membutton-{:03}" class="memory_button" style="background:none; border:none;" data-mv_address="{}" onclick="script.script_interact_button(event)">{:02X}</button>'.format(self.script_ids[-1], index+self.start_address, self.start_address+(index), self.memory_buffer[index])
                    self.html_data += '</ons-col>\n'
            self.html_data += '</ons-row>'
        return self.html_data

    def direction_pressed(self, name, _id, data):
        self.on_direction(data['data']['direction'], (self.max_rows * (self.max_cols-1)))


    def handle_interaction(self, _id: str, data):
        if 'membutton' in _id:
            self.handle_selection(_id, data)

    def on_copy(self, name, ele_id, data):
        res = self.get_element("OUTPUT_ADDRESS_STRING").get_text()
        cast(controls.advanced.CopyButton, self.get_element("COPY_BUTTON")).copy({'address': res})


    def set_data(self, data:bytes, address: int = 0):
        old_data = self.memory_buffer
        self.memory_buffer = data
        self.last_start_address = self.start_address
        self.start_address = address
        if self.start_address != self.last_start_address:
            html = self.generate()
            self.get_element("MEMORY_ROW").inner(html)

        if self.start_address <= self.current_selected_address < self.start_address+len(data):
            self.js('if ($(".memory_button").css("border").indexOf("none") >= 0) {{ $("[data-mv_address=\'{}\']").css("border", "solid"); $("[data-mv_address=\'{}\']").css("border-width", "1px"); }}'.format(self.current_selected_address, self.current_selected_address))
            dl = self.check_for_diff(old_data, data)
            if self.current_selected_address in dl:
                self.fill_data(self.current_selected_address - self.start_address)
        else:
            self.js('$(".memory_button").css("border", "none"); $("[data-mv_address=\'{}\']").css("border", "solid"); $("[data-mv_address=\'{}\']").css("border-width", "1px");'.format(address, address))
            cast(controls.Input, self.get_element("OUTPUT_ADDRESS_STRING")).set_text("{:X}".format(address))
            self.fill_data(0)
            self.current_selected_address = address

    def fill_data(self, location: int):
        l = location
        [cast(controls.Input, self.get_element(k)).set_text("{}".format(unpack(self.ctrl_map[k]['pack'], self.memory_buffer[l:self.ctrl_map[k]['size'] + l])[0])) for k in self.ctrl_keys if l+self.ctrl_map[k]['size']-1 < len(self.memory_buffer)]
        [cast(controls.Input, self.get_element(k)).set_text("") for k in self.ctrl_keys if l + self.ctrl_map[k]['size'] - 1 >= len(self.memory_buffer)]


    def check_for_diff(self, old_data: bytes, new_data: bytes):
        diff_list = []
        if old_data:
            for i in range(0, len(new_data)):
                if old_data[i] != new_data[i]:
                    diff_list.append(i + self.start_address)
        if diff_list:
            js_string = ""
            for data_address in diff_list:
                js_string += '$("[data-mv_address=\'{}\']").addClass("flash"); '.format(data_address)
                js_string += 'setTimeout(function() {{ $("[data-mv_address=\'{}\']").removeClass("flash"); }}, 500);  '.format(data_address)
                js_string += '$("[data-mv_address=\'{}\']").html(\'{:02X}\'); '.format(data_address, new_data[data_address-self.start_address])
            self.js(js_string)
        return diff_list

    def handle_selection(self, _id, data):
        self.current_selected_address = data['data']['mv_address']
        address = '{:X}'.format(data['data']['mv_address'])
        cast(controls.Input, self.get_element("OUTPUT_ADDRESS_STRING")).set_text(address)
        self.fill_data(data['data']['mv_address'] - self.start_address)
        self.js('$(".memory_button").css("border", "none"); $("#{}").css("border", "solid"); $("#{}").css("border-width", "1px");'.format(_id, _id))

    def invalid_input(self, _id, pos):
        val = unpack(self.ctrl_map[_id]['pack'], self.memory_buffer[pos: pos+self.ctrl_map[_id]['size']])[0]
        self.get_element(_id).set_text(str(val))

    def get_count(self):
        return self.max_cols * self.max_rows

    def value_changed(self, _id, ele, data):
        l = self.current_selected_address - self.start_address
        if l+self.ctrl_map[_id]['size']-1 >= len(self.memory_buffer):
            self.get_element(_id).set_text("")
            return

        try:
            if 'FLOAT' in _id:
                cv = float(data['value'])
            else:
                cv = int(data['value'])
        except ValueError:
            self.invalid_input(_id, self.current_selected_address - self.start_address)
            return
        if cv < self.ctrl_map[_id]['min']:
            cv = self.ctrl_map[_id]['min']
        if cv > self.ctrl_map[_id]['max']:
            cv = self.ctrl_map[_id]['max']

        if cv != unpack(self.ctrl_map[_id]['pack'] , self.memory_buffer[l:self.ctrl_map[_id]['size'] + l])[0]:
            self.on_write(self.current_selected_address, self.ctrl_map[_id]['type'](cv))

    def clear_data(self):
        pass






