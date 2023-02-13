import ctypes
import json
import platform
from pathlib import Path
from struct import unpack
from threading import Event
from threading import Thread
from typing import cast
from math import isnan

from app.script_common import BaseScript
from app.script_ui import controls
from app.script_ui.validators import address_match, region_match
from .trend_calculator import calculate_trend
from .trend_results import TrendResultsGroup
from .trend_row import TrendRow


class TrendSearch(BaseScript):
    TREND_STATE_PROC = 0
    TREND_STATE_START = 1
    TREND_STATE_CAPTURE = 2
    TREND_STATE_CAPTURE_COMPLETE = 3
    TREND_STATE_ANALYZE = 4

    def on_load(self):
        self.put_data("SYSTEM", platform.system())
        self.put_data("CAPTURE_EVENT", Event())
        self.put_data("CAPTURE_COMPETE", False)
        self.put_data("CAPTURE_STATE", self.TREND_STATE_PROC)
        self.put_data("CAPTURE_PATH", Path(self.directory).joinpath('.capture'))

    def get_script_information(self):
        return {
            'title': "Trend Search",
            'author': "Ryan Kegel",
            'version': '1.0.0'}

    def get_state(self):
        return self.get_data("CAPTURE_STATE")

    def build_ui(self):
        ps_page = self.ui.add_page(controls.Page())
        capture_page = self.ui.add_page(controls.Page(id='CAPTURE_PAGE'))
        ps_page.add_elements([controls.advanced.ProcessSelect(self.process_selected, id='PROCS')])

        self.ui.set_page_header(ps_page, "Process Select")

        self.ui.set_page_header(capture_page, "Trend Capture")

        capture_page.add_elements([
            controls.Text("Capture Near Address:", width="190px"),
            controls.Input(on_change=self.ctrl_changed, id='INPUT_CAPTURE_ADDRESS', trigger_by_focus=False),
            controls.advanced.PasteButton(on_click=self.on_paste, id='PASTE_CAPTURE_ADDRESS')])

        capture_page.add_elements([
            controls.Text("Capture Range [12-16384]:", width="190px"),
            controls.Input(on_change=self.ctrl_changed,  text="4096", id='INPUT_CAPTURE_RANGE', trigger_by_focus=False)])

        capture_page.add_elements([
            controls.Text("Capture Delay:", width="190px"),
            controls.Input(on_change=self.ctrl_changed, text="0.0", id='INPUT_CAPTURE_DELAY', trigger_by_focus=False)])

        capture_page.add_elements([
            controls.Button("Start", on_click=self.start_capture, id='BUTTON_START_CAPTURE'),
            controls.Button("Stop", on_click=self.stop_capture, id='BUTTON_STOP_CAPTURE')], id="ROW_START_STOP")

        capture_page.add_elements([
            controls.Text("Status", id='TEXT_CAPTURE_STATUS')], id="ROW_CAPTURE_STATUS")

        analysis_page = self.ui.add_page(controls.Page(id='ANALYSIS_PAGE'))
        self.ui.set_page_header(analysis_page,  "Trend Analysis")
        analysis_page.add_element(TrendRow(on_clicked=self.trend_clicked, id='ROW_TREND'))
        analysis_page.add_elements([
            controls.Text("Value Type:", width="190px"),
            controls.Select([('byte_1', '1'), ('byte_2', '2'),('byte_4', '4'),('byte_8', '8'),('float', 'FLOAT')], on_change=self.ctrl_changed, id='SELECT_VALUE_TYPE')])
        analysis_page.add_elements([
            controls.Text("Signed Value:", width="190px"),
            controls.Toggle(on_toggle=self.ctrl_changed, id='TOGGLE_VALUE_SIGNED')])
        analysis_page.add_elements([
            controls.Button("Calculate", on_click=self.on_calculate_trend, id='BUTTON_CALCULATE_TREND')])
        analysis_page.add_elements([
            controls.Text("Status", id='TEXT_TREND_RESULT_STATUS')])
        analysis_page.add_elements([
            TrendResultsGroup(on_copy=None, on_max=self.on_max_pressed, on_min=self.on_min_pressed, id='GROUP_TREND_RESULTS')])


    def on_ready(self):
        self.ui.get_element("CAPTURE_PAGE").hide()
        self.ui.get_element("ANALYSIS_PAGE").hide()
        self.ui.get_element("TEXT_CAPTURE_STATUS").hide()
        self.ui.get_element("TEXT_TREND_RESULT_STATUS").hide()
        self.ui.get_element("BUTTON_CALCULATE_TREND").disable()

    def on_reload(self):
        proc = self.get_data("PROCESS")
        self.process_selected(proc)

    def find_min_max(self, data, min_selected=True):
        sg: controls.Toggle = self.ui.get_element("TOGGLE_VALUE_SIGNED")
        tp: controls.Select = self.ui.get_element("SELECT_VALUE_TYPE")
        tp_value = tp.get_selection()
        signed = sg.is_checked()
        addr = data['address']
        if min_selected:
            value = min(self.get_data("CURRENT_TREND_DATA")[int(data['key'])])
        else:
            value = max(self.get_data("CURRENT_TREND_DATA")[int(data['key'])])

        if tp_value == 'byte_1':
            c_val = ctypes.c_int8(value) if signed else ctypes.c_uint8(value)
        elif tp_value == 'byte_2':
            c_val = ctypes.c_int16(value) if signed else ctypes.c_uint16(value)
        elif tp_value == 'byte_4':
            c_val = ctypes.c_int32(value) if signed else ctypes.c_uint32(value)
        elif tp_value == 'byte_8':
            c_val = ctypes.c_int64(value) if signed else ctypes.c_uint64(value)
        else:
            c_val = ctypes.c_float(value)
        return addr, c_val

    def on_max_pressed(self, name, _id, data):
        addr, c_val = self.find_min_max(data, min_selected=False)
        self.memory_manager.memory.write_memory(addr, c_val)


    def on_min_pressed(self, name, _id, data):
        addr, c_val = self.find_min_max(data, min_selected=True)
        self.memory_manager.memory.write_memory(addr, c_val)


    def process_selected(self, proc):
        if proc is None:
            self.put_data("PROCESS", None)
            self.ui.get_element("CAPTURE_PAGE").hide()
            self.ui.get_element("ANALYSIS_PAGE").hide()
        else:
            self.put_data("PROCESS", proc)
            self.ui.get_element("CAPTURE_PAGE").show()
            self.check_for_calculate()
            self.check_for_start()

    def ctrl_changed(self, name: str, ele_id: str, data):
        if name == 'INPUT_CAPTURE_ADDRESS' or name == 'INPUT_CAPTURE_RANGE' or name == 'INPUT_CAPTURE_DELAY':
            self.check_for_start()

    def trend_clicked(self, name: str, ele_id: str, data):
        tr: TrendRow = self.ui.get_element("ROW_TREND")
        tl = tr.get_trend_list()
        if len(tl) > 1 and not all(x == tl[0] for x in tl):
            self.ui.get_element("BUTTON_CALCULATE_TREND").enable()
        else:
            self.ui.get_element("BUTTON_CALCULATE_TREND").disable()

    def check_for_start(self):
        self.ui.get_element("BUTTON_STOP_CAPTURE").disable()
        address = self.ui.get_element('INPUT_CAPTURE_ADDRESS').get_text()
        try:
            _range = int(self.ui.get_element('INPUT_CAPTURE_RANGE').get_text())
            delay = float(self.ui.get_element('INPUT_CAPTURE_DELAY').get_text())
        except ValueError:
            self.ui.get_element("ROW_START_STOP").hide()
            return
        if not ((address_match(address) or region_match(address)) and 12 <= _range <= 16384 and 0.0 <= delay <= 10.0):
            self.ui.get_element("ROW_START_STOP").hide()
            return

        if ':' in address:
            addr = self.memory_manager.get_address(address)
            if addr is None:
                self.ui.get_element("ROW_START_STOP").hide()
                return
        else:
            addr = int(address, 16)

        location = self.get_location(addr, int(_range))
        if location is None:
            self.ui.get_element("ROW_START_STOP").hide()
            return
        self.put_data("CAPTURE_INPUT", {'start': location[0], 'end': location[1], 'delay': delay})
        self.ui.get_element("BUTTON_STOP_CAPTURE").disable()
        self.ui.get_element("BUTTON_START_CAPTURE").enable()
        self.ui.get_element("ROW_START_STOP").show()

    def check_for_calculate(self):
        if self.has_captures():
            self.ui.get_element("ANALYSIS_PAGE").show()
        else:
            self.ui.get_element("ANALYSIS_PAGE").hide()

    def on_paste(self, name: str, ele_id: str, data):
        if name == 'PASTE_CAPTURE_ADDRESS':
            self.ui.get_element("INPUT_CAPTURE_ADDRESS").set_text(self.get_data("CLIPBOARD")['address'].upper())
            self.check_for_start()

    def on_clipboard_copy(self, data):
        show_paste_address = False
        if 'address' in data and 'offsets' in data:
            show_paste_address = True
            if 'resolved' in data:
                self.put_data("CLIPBOARD", {'address': data['resolved']})
            else:
                self.put_data("CLIPBOARD", {'address': data['address']})
        elif 'address' in data:
            self.put_data("CLIPBOARD", {'address': data['address']})
            show_paste_address = True
        self.ui.get_element("PASTE_CAPTURE_ADDRESS").show() if show_paste_address else self.ui.get_element("PASTE_CAPTURE_ADDRESS").hide()


    def on_clipboard_clear(self):
        self.ui.get_element("PASTE_CAPTURE_ADDRESS").hide()

    def stop_capture(self, _1, _2, _3):
        self.ui.get_element("BUTTON_STOP_CAPTURE").disable()
        cap_thread: Thread = self.get_data("CAPTURE_THREAD")
        evt: Event = self.get_data("CAPTURE_EVENT")
        evt.set()
        if cap_thread and cap_thread.is_alive():
            cap_thread.join()
        self.check_for_start()
        self.check_for_calculate()

    def frame(self):
        if self.get_data("CAPTURE_COMPLETE"):
            self.put_data("CAPTURE_COMPLETE", False)
            self.check_for_start()
            self.check_for_calculate()

    def start_capture(self, _1, _2, _3):
        self.put_data("CAPTURE_COMPLETE", False)
        self.put_data("CAPTURE_EVENT", Event())
        self.ui.get_element("BUTTON_STOP_CAPTURE").enable()
        self.ui.get_element("BUTTON_START_CAPTURE").disable()
        self.ui.get_element("TEXT_CAPTURE_STATUS").set_text('Setting up capture...')
        self.ui.get_element("TEXT_CAPTURE_STATUS").show()
        cap_thread = Thread(target=self.capture)
        self.put_data("CAPTURE_THREAD", cap_thread)
        cap_thread.start()

    def delay(self, delay: float, event: Event):
        while delay > 0 and not event.is_set():
            self.ui.get_element("TEXT_CAPTURE_STATUS").set_text('Capture starts in {:.1f} seconds'.format(delay))
            event.wait(0.3)
            delay -= 0.3

    def capture(self):
        capture_inputs = self.get_data("CAPTURE_INPUT")
        start = capture_inputs['start']
        end = capture_inputs['end']
        delay = capture_inputs['delay']
        region_buffer = (ctypes.c_byte * (end - start))()
        event: Event = self.get_data("CAPTURE_EVENT")
        path: Path = self.get_data("CAPTURE_PATH")
        path.mkdir(parents=True, exist_ok=True)
        [x.unlink(missing_ok=True) for x in path.glob('*.cap')]
        if delay > 0:
            self.delay(delay, event)
            if event.is_set():
                self.put_data("CAPTURE_COMPLETE", True)
                return
        self.ui.get_element("TEXT_CAPTURE_STATUS").set_text('Capturing from {:X} to {:X}'.format(start, end))
        cap_info = path.joinpath('capture_info')
        cap_info.write_text(json.dumps({'start': start, 'end': end, 'size': end-start}))
        for i in range(0, 50): #10 second max interval
            self._capture(start, end, region_buffer, path.joinpath('trend_{:03}.cap'.format(i)))
            event.wait(0.2)
            if event.is_set():
                break
        self.ui.get_element("TEXT_CAPTURE_STATUS").hide()
        self.put_data("CAPTURE_COMPLETE", True)

    def get_capture_files(self):
        path: Path = self.get_data("CAPTURE_PATH")
        return sorted(list(path.glob('trend_*.cap')))

    def _capture(self, start:int, end:int, buffer, capture_file):
        self.memory.read_memory(start, buffer)
        capture_file.write_bytes(bytes(buffer))

    def get_location(self, addr: int, range: int):
        loc_start = -1
        loc_stop = -1
        pm = self.memory_manager.get_process_map()
        for item in pm:
            if addr < item['start'] or addr >= item['stop']:
                continue
            loc_start = item['start']
            loc_stop = item['stop']
        if loc_start < 0:
            return None

        p_start = int(addr - range/2) - (int(addr - range/2) % 8)
        p_end = int(addr + range/2) + (int(addr + range/2) % 8)
        _start = int(max(p_start, loc_start))
        _end = int(min(p_end, loc_stop))
        return _start, _end

    def on_calculate_trend(self, _1, _2, _3):
        tr: TrendRow = self.ui.get_element("ROW_TREND")
        sg: controls.Toggle = self.ui.get_element("TOGGLE_VALUE_SIGNED")
        tp: controls.Select = self.ui.get_element("SELECT_VALUE_TYPE")
        path: Path = self.get_data("CAPTURE_PATH")
        cap_info = json.loads(path.joinpath("capture_info").read_text())
        data = self.load_captures(size=tp.get_selection(), signed=sg.is_checked())
        valid_keys = calculate_trend(tr.get_trend_list(), data)
        new_data = {}
        for k in valid_keys:
            new_data[k] = data[k]
        self.put_data("CURRENT_TREND_DATA", new_data)
        cast(TrendResultsGroup, self.ui.get_element("GROUP_TREND_RESULTS")).set_trend_data(new_data, cap_info)
        if len(valid_keys) > 0:
            self.ui.get_element("TEXT_TREND_RESULT_STATUS").set_text('Found {} possible results.'.format(len(valid_keys)))
        else:
            self.ui.get_element("TEXT_TREND_RESULT_STATUS").set_text('0 results found with this trend.')
        self.ui.get_element("TEXT_TREND_RESULT_STATUS").show()


    def load_captures(self, size: str, signed: bool) -> dict:
        data = {}
        for f in self.get_capture_files():
            file_data = f.read_bytes()
            if size == 'float':
                for i in range(0, len(file_data), 4):
                    [val] = unpack('f', file_data[i:i+4])
                    if i not in data:
                        data[i] = []
                    if isnan(val):
                        val = 0.0
                    data[i].append(val)
            else:
                sz = 4
                if size == 'byte_1':
                    sz = 1
                elif size == 'byte_2':
                    sz = 2
                elif size == 'byte_8':
                    sz = 8
                for i in range(0, len(file_data), sz):
                    val = int.from_bytes(file_data[i:i+sz], byteorder='little', signed=signed)
                    if i not in data:
                        data[i] = []
                    data[i].append(val)
        return data

    def has_captures(self) -> bool:
        path: Path = self.get_data("CAPTURE_PATH")
        return len(self.get_capture_files()) > 1 and path.joinpath("capture_info").exists()
