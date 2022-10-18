import copy
import ctypes
import json
import os
from pathlib import Path
from threading import Thread, Lock, Event
from typing import Union

from falcon import Request, Response
from falcon.app_helpers import MEDIA_JSON

from app.helpers import DynamicHTML, MemoryHandler
from app.helpers import memory_utils
from app.helpers.exceptions import CodelistException
from app.helpers.memory_utils import get_ctype
from app.script_common.aob import AOB
from app.script_common.utilities import ScriptUtilities

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]


class CodeList(MemoryHandler):
    directory = Path('codes')
    def __init__(self):
        super().__init__('codelist')
        self.handle_map = {
            "CODELIST_GET": self.handle_get,
            "CODELIST_LOAD": self.handle_load,
            "CODELIST_STATUS": self.handle_status,
            "CODELIST_WRITE": self.handle_write,
            "CODELIST_FREEZE": self.handle_freeze,
            "CODELIST_NAME": self.handle_name,
            "CODELIST_SIZE": self.handle_size,
            "CODELIST_REFRESH": self.handle_refresh,
            "CODELIST_DELETE_CODE": self.handle_delete_code,
            "CODELIST_SAVE": self.handle_save,
            "CODELIST_DELETE_LIST": self.handle_delete_list,
            "CODELIST_ADD_CODE": self.handle_add_code,
        }
        self.update_thread: Thread = None
        self.update_event: Event = None
        self.update_lock: Lock = Lock()

        self.freeze_thread: Thread = None
        self.freeze_event: Event = None

        self.code_data = None
        self.loaded_file = "_null"
        self.aob_map = {}
        self.result_list = []
        self.freeze_map = {}
        self.utilities = ScriptUtilities()

    def kill(self):
        self.reset()

    def release(self):
        self.reset()

    def process_error(self, msg: str):
        self.reset()

    def set(self, data):
        pass

    def reset(self):
        self.stop_freezer()
        self.stop_updater()
        self.code_data = None
        self.loaded_file = "_null"
        self.aob_map.clear()
        self.result_list.clear()
        self.freeze_map.clear()


    def html_main(self):
        return DynamicHTML('resources/codelist.html', 1).get_html()

    def handle_get(self, req: Request, resp: Response):
        resp.media['files'] = self.get_code_files()
        resp.media['repeat'] = 1000 if self.code_data else 0
        resp.media['file'] = self.loaded_file
        if self.code_data:
            resp.media['file_data'] = self.code_data
            print(self.code_data)

    def handle_status(self, req: Request, resp: Response):
        resp.media['repeat'] = 1000 if self.code_data else 0
        if self.code_data:
            resp.media['results'] = []
            with self.update_lock:
                results = self.get_results()
                for i in range(0, len(results)):
                    result = results[i]
                    value = str(result['Value'].value) if result['Value'] is not None else '??'
                    res = {'Value': value}
                    if 'Addresses' in result:
                        res['Addresses'] = result['Addresses']
                    resp.media['results'].append(res)

    def handle_write(self, req: Request, resp: Response):
        index = int(req.media['index'])
        if index < 0 or index >= len(self.code_data):
            raise CodelistException("Can't write code that isn't in the list")
        code = self.code_data[index]
        try:
            b = self.determine_value(req.media['value'], code)
        except ValueError:
            raise CodelistException("Could not write that value")
        if index in self.freeze_map:
            with self.update_lock:
                self.freeze_map[index]['value'] = b
            return

        if code['Source'] == 'address':
            with self.update_lock:
                code['Value'] = str(b.value)
                self.mem().write_memory(code['Address'], b)
        else:
            if code['AOB'] not in self.aob_map:
                raise CodelistException('Could not write AOB value because it cannot be found')
            with self.update_lock:
                code['Value'] = str(b.value)
                for base in self.aob_map[code['AOB']].get_bases():
                    self.mem().write_memory(base+int(code['Offset'], 16), b)

    def handle_freeze(self, req: Request, resp: Response):
        frozen = req.media['freeze'] == 'true'
        index = int(req.media['index'])
        if index < 0 or index >= len(self.code_data):
            raise CodelistException("Can't write code that isn't in the list")
        with self.update_lock:
            value = copy.copy(self.get_results()[index])
            code = self.code_data[index]
            code['Freeze'] = frozen
            if frozen:
                self.freeze_map[index] = {'value': value['Value'], 'index': index, 'code': code}
            else:
                if index in self.freeze_map:
                    del self.freeze_map[index]

        if not (self.freeze_thread and self.freeze_thread.is_alive()) and self.freeze_map:
            self.start_freezer()
        if not self.freeze_map:
            self.stop_freezer()


    def handle_size(self, req: Request, resp: Response):
        size = req.media['size']
        index = int(req.media['index'])
        if index < 0 or index >= len(self.code_data):
            raise CodelistException("Can't write code that isn't in the list")
        code = self.code_data[index]
        with self.update_lock:
            code['Type'] = size
            if index in self.freeze_map:
                value = memory_utils.limit(self.freeze_map[index]['value'].value, size)
                self.freeze_map[index]['value'] = get_ctype(str(value), size)(value)

    def handle_delete_code(self, req: Request, resp: Response):
        index = int(req.media['index'])
        if index < 0 or index >= len(self.code_data):
            raise CodelistException("Can't write code that isn't in the list")
        with self.update_lock:
            if index in self.freeze_map:
                del self.freeze_map[index]
        self.code_data.pop(index)
        resp.media['file_data'] = self.code_data

    def handle_add_code(self, req: Request, resp: Response):
        tp = req.media['type']
        if not self.code_data:
            self.code_data = []
        with self.update_lock:
            if 'index' in req.media:
                index = int(req.media['index'])
                cd = self.code_data[index]
                if index in self.freeze_map:
                    del self.freeze_map[index]
                    cd['Freeze'] = False
                if tp == 'address':
                    cd['Source'] = 'address'
                    cd['Address'] = int(req.media['address'], 16)
                    if 'AOB' in cd:
                        del cd['AOB']
                    if 'Offset' in cd:
                        del cd['Offset']
                else:
                    cd['Source'] = 'aob'
                    cd['AOB'] = req.media['aob'].upper()
                    cd['Offset'] = req.media['offset'].upper()
                    if 'Address' in cd:
                        del cd['Address']
            else:
                index = len(self.code_data)+1
                if tp == 'address':
                    self.code_data.append({
                        "Name": "Code #{}".format(index),
                        "Type": "byte_4",
                        "Signed": False,
                        "Freeze": False,
                        "Source": "address",
                        "Address": int(req.media['address'], 16)
                    })
                else:
                    self.code_data.append({
                        "Name": "Code #{}".format(index),
                        "Type": "byte_4",
                        "Signed": False,
                        "Freeze": False,
                        "Source": "aob",
                        "AOB": req.media['aob'].upper(),
                        "Offset": req.media['offset'].upper()
                    })
        resp.media['file_data'] = self.code_data
        if not (self.freeze_thread and self.freeze_thread.is_alive()) and self.freeze_map:
            self.start_freezer()
        if not self.freeze_map:
            self.stop_freezer()
        if not (self.update_thread and self.update_thread.is_alive()):
            self.start_updater()
            resp.media['repeat'] = 1000

    def handle_save(self, req: Request, resp: Response):
        file = req.media['file']
        write_data = copy.copy(self.code_data)
        try:
            for item in write_data:
                if 'Value' in item:
                    del item['Value']
            pt = self.directory.joinpath(file+'.codes')
            with open(pt, 'wt') as f:
                json.dump(write_data, f, indent=4)
        except:
            raise CodelistException('Could not save codes.')
        if pt.stem != self.loaded_file:
            self.loaded_file = pt.stem
            resp.media['file_data'] = self.code_data
            resp.media['file'] = self.loaded_file
            resp.media['files'] = self.get_code_files()

    def handle_delete_list(self, req: Request, resp: Response):
        file = req.media['file']
        self.reset()
        try:
            pt = self.directory.joinpath(file+'.codes')
            os.unlink(str(pt.absolute()))
        except:
            raise CodelistException('Could not remove code file.')
        resp.media['file_data'] = []
        resp.media['file'] = self.loaded_file
        resp.media['files'] = self.get_code_files()




    def handle_name(self, req: Request, resp: Response):
        name = req.media['name']
        index = int(req.media['index'])
        if index < 0 or index >= len(self.code_data):
            raise CodelistException("Can't write code that isn't in the list")
        code = self.code_data[index]
        with self.update_lock:
            code['Name'] = name

    def handle_refresh(self, req: Request, resp: Response):
        index = int(req.media['index'])
        if index < 0 or index >= len(self.code_data):
            raise CodelistException("Can't write code that isn't in the list")
        code = self.code_data[index]
        if code['Type'] == 'address':
            return
        aob_str = code['AOB']
        if aob_str not in self.aob_map:
            return
        self.aob_map[aob_str].clear_bases()

    def handle_load(self, req: Request, resp: Response):
        if req.media['file'] == '_null':
            self.stop_freezer()
            self.stop_updater()
            self.code_data = None
            self.loaded_file = "_null"
            resp.media['file_data'] = self.code_data
            resp.media['file'] = self.loaded_file
            return
        pt = self.directory.joinpath(req.media['file']+'.codes')
        if not pt.exists():
            raise CodelistException('Code file not found')
        try:
            with open(pt, 'rt') as ifile:
                self.code_data = json.load(ifile)
                for v in self.code_data:
                    v['Value'] = "??"
                self.loaded_file = pt.stem
        except:
            raise CodelistException('Could not load code file')
        resp.media['file_data'] = self.code_data
        resp.media['file'] = self.loaded_file
        resp.media['repeat'] = 1000
        self.start_updater()

    def process(self, req: Request, resp: Response):
        resp.media = {}
        command = req.media['command']
        assert (command in self.handle_map)
        resp.content_type = MEDIA_JSON
        try:
            self.handle_map[command](req, resp)
        except CodelistException as e:
            resp.media['error'] = e.get_message()
        finally:
            pass

    def get_code_files(self):
        pt = self.directory.glob('*.codes')
        return [x.stem for x in pt]


    def read_aob_value(self, aob: AOB, code):
        offset = int(code['Offset'], 16)
        if aob.is_found():
            bases = aob.get_bases()
            for i in range(len(bases) - 1, -1, -1):
                base = bases[i]
                res, _, _ = self.utilities.compare_aob(self.mem(), base, aob)
                if not res:
                    bases.pop(i)
            if not bases:
                aob.clear_bases()
            else:
                return self.get_read(code, aob.get_bases()[0] + offset), [x+offset for x in aob.get_bases()]

        if not aob.is_found():
            addrs = self.utilities.search_aob_all_memory(self.mem(), aob)
            if not addrs:
                aob.clear_bases()
            else:
                aob.set_bases([x['address'] for x in addrs])
                return self.get_read(code, addrs[0]['address'] + offset), [x+offset for x in aob.get_bases()]
        return None, []

    def _update_process(self):
        while not self.update_event.is_set():
            with self.update_lock:
                self.result_list.clear()
                for code in self.code_data:
                    if code['Source'] == 'address':
                        addr = code['Address']
                        try:
                            read = self.get_read(code, addr)
                        except OSError:
                            read = None
                        self.result_list.append({'Value': read})
                    else:
                        aob_str = code['AOB']
                        if aob_str not in self.aob_map:
                            self.aob_map[aob_str] = AOB(code['Name'], aob_str)
                        try:
                            read, addrs = self.read_aob_value(self.aob_map[aob_str], code)
                        except OSError:
                            read, addrs = (None, None)
                        self.result_list.append({'Value': read, 'Addresses': addrs})
            self.update_event.wait(0.5)

    def get_read(self, code, addr: int):
        raw = memory_utils.get_ctype_from_size(code['Type'])
        self.mem().read_memory(addr, raw)
        return memory_utils.get_ctype_from_buffer(raw, code['Type'], code['Signed'])


    def determine_value(self, value:str, code):
        was_signed = code['Signed']
        if code['Type'] == 'float':
            return ctypes.c_float(float(value))
        value = int(value)
        if was_signed:
            if code['Type'] == 'byte_1':
                if value > 0x7F:
                    code['Signed'] = False
                value = max(-0x7F, min(0xFF, value))
            elif code['Type'] == 'byte_2':
                if value > 0x7FFF:
                    code['Signed'] = False
                value = max(-0x7FFF, min(0xFFFF, value))
            elif code['Type'] == 'byte_4':
                if value > 0x7FFFFFFF:
                    code['Signed'] = False
                value = max(-0x7FFFFFFF, min(0xFFFFFFFF, value))
        else:
            if value < 0:
                code['Signed'] = True
            if code['Type'] == 'byte_1':
                value = max(-0x7F, min(0xFF, value))
            elif code['Type'] == 'byte_2':
                value = max(-0x7FFF, min(0xFFFF, value))
            elif code['Type'] == 'byte_2':
                value = max(-0x7FFFFFFF, min(0xFFFFFFFF, value))
        return memory_utils.get_ctype_from_int_value(value, code['Type'], code['Signed'])




    def start_updater(self):
        self.update_thread = Thread(target=self._update_process)
        self.update_event = Event()
        self.update_thread.start()

    def stop_updater(self):
        if self.update_thread and self.update_thread.is_alive():
            self.update_event.set()
            self.update_thread.join()

    def get_results(self):
        res = self.result_list.copy()
        return res

    def _freeze_process(self):
        while not self.freeze_event.is_set():
            with self.update_lock:
                for key, value in self.freeze_map.items():
                    addrs = self.get_addresses(value['code'])
                    for addr in addrs:
                        self.mem().write_memory(addr, value['value'])
            self.freeze_event.wait(0.5)

    def get_addresses(self, code):
        address_list = []
        if code['Source'] == 'address':
            address_list.append(code['Address'])
        else:
            if code['AOB'] not in self.aob_map:
                raise CodelistException('Cannot find AOB in map for freeze')
            aob = self.aob_map[code['AOB']]
            bases = aob.get_bases()
            for b in bases:
                res, _, _ = self.utilities.compare_aob(self.mem(), b, aob)
                if res:
                    address_list.append(b + int(code['Offset'], 16))
        return address_list




    def start_freezer(self):
        self.freeze_thread = Thread(target=self._freeze_process)
        self.freeze_event = Event()
        self.freeze_thread.start()

    def stop_freezer(self):
        if self.freeze_thread and self.freeze_thread.is_alive():
            self.freeze_event.set()
            self.freeze_thread.join()








