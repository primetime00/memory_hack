import copy
import ctypes
import json
import os
from threading import Thread, Lock, Event
from typing import Union

from falcon import Request, Response
from falcon.app_helpers import MEDIA_JSON

from app.helpers import DynamicHTML, MemoryHandler
from app.helpers import memory_utils
from app.helpers.directory_utils import codes_directory
from app.helpers.exceptions import AOBException
from app.helpers.exceptions import CodelistException
from app.helpers.memory_utils import get_ctype
from app.helpers.process import BaseConvert
from app.script_common.aob import AOB
from app.script_common.utilities import ScriptUtilities

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]


class CodeList(MemoryHandler):
    directory = codes_directory
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
            "CODELIST_AOB_SELECT": self.handle_aob_base_select
        }
        self.update_thread: Thread = None
        self.update_event: Event = None
        self.update_lock: Lock = Lock()

        self.freeze_thread: Thread = None
        self.freeze_event: Event = None

        self.code_data = None
        self.loaded_file = "_null"
        self.aob_map = {}
        self.result_map = {}
        self.freeze_map = {}
        self.utilities: ScriptUtilities = None
        self.process_map = None
        self.base_lookup_map = {}
        self.component_index = 0
        self.base_converter = BaseConvert()

        if not self.directory.exists():
            self.directory.mkdir(parents=True, exist_ok=True)

    def kill(self):
        self.reset()

    def release(self):
        self.reset()

    def process_error(self, msg: str):
        self.reset()

    def set(self, data):
        self.utilities = ScriptUtilities(self.mem(), "codelist")

    def reset(self):
        self.stop_freezer()
        self.stop_updater()
        self.code_data = None
        self.loaded_file = "_null"
        self.aob_map.clear()
        self.result_map.clear()
        self.freeze_map.clear()
        self.component_index = 0


    def html_main(self):
        return DynamicHTML('resources/codelist.html', 1).get_html()

    def handle_get(self, req: Request, resp: Response):
        resp.media['files'] = self.get_code_files()
        resp.media['repeat'] = 1000 if self.code_data else 0
        resp.media['file'] = self.loaded_file
        if self.code_data:
            resp.media['file_data'] = self.code_data

    def handle_status(self, req: Request, resp: Response):
        resp.media['repeat'] = 1000 if self.code_data else 0
        if self.code_data:
            resp.media['results'] = []
            with self.update_lock:
                resp.media['results'] = self.get_results()

    def handle_write(self, req: Request, resp: Response):
        index = int(req.media['index'])
        if index not in self.code_data:
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
                addr = self.base_converter.convert(self.mem(), code['Address'])
                self.mem().write_memory(addr, b)
        elif code['Source'] == 'pointer':
            with self.update_lock:
                if 'Resolved' in code and code['Resolved'] > 0:
                    self.mem().write_memory(code['Resolved'], b)
        else:
            if code['AOB'] not in self.aob_map:
                raise CodelistException('Could not write AOB value because it cannot be found')
            with self.update_lock:
                for base in self.aob_map[code['AOB']].get_bases():
                    self.mem().write_memory(base+int(code['Offset'], 16), b)

    def handle_freeze(self, req: Request, resp: Response):
        frozen = req.media['freeze'] == 'true'
        index = int(req.media['index'])
        if index not in self.code_data:
            raise CodelistException("Can't write code that isn't in the list")
        with self.update_lock:
            value = copy.copy(self.get_results()[index])

            code = self.code_data[index]
            code['Freeze'] = frozen
            if frozen:
                dt = memory_utils.typeToCType[(code['Type'], code['Signed'])]
                self.freeze_map[index] = {'value': dt(value['Value']['Actual']), 'index': index, 'code': code}
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
        if index not in self.code_data:
            raise CodelistException("Can't write code that isn't in the list")
        code = self.code_data[index]
        with self.update_lock:
            code['Type'] = size
            if index in self.freeze_map:
                value = memory_utils.limit(self.freeze_map[index]['value'].value, size)
                self.freeze_map[index]['value'] = get_ctype(str(value), size)(value)

    def handle_delete_code(self, req: Request, resp: Response):
        index = int(req.media['index'])
        if index not in self.code_data:
            raise CodelistException("Can't write code that isn't in the list")
        with self.update_lock:
            if index in self.freeze_map:
                del self.freeze_map[index]
        del self.code_data[index]
        if index in self.result_map:
            del self.result_map[index]
        resp.media['remove_index'] = index

    def handle_add_code(self, req: Request, resp: Response):
        tp = req.media['type']
        if not self.code_data:
            self.code_data = {}
        with self.update_lock:
            if 'index' in req.media:
                index = int(req.media['index'])
                cd = self.code_data[index]
                if index in self.freeze_map:
                    del self.freeze_map[index]
                    cd['Freeze'] = False
                if tp == 'address':
                    cd['Source'] = 'address'
                    cd['Address'] = req.media['address']
                    if 'AOB' in cd:
                        del cd['AOB']
                    if 'Offset' in cd:
                        del cd['Offset']
                    if 'Offsets' in cd:
                        del cd['Offsets']
                    if 'Value' in cd:
                        del cd['Value']
                elif tp == 'pointer':
                    cd['Source'] = 'pointer'
                    cd['Address'] = req.media['address']
                    cd['Offsets'] = req.media['offsets']
                    cd['Resolved'] = '????????'
                    if 'AOB' in cd:
                        del cd['AOB']
                    if 'Offset' in cd:
                        del cd['Offset']
                    if 'Value' in cd:
                        del cd['Value']
                else:
                    cd['Source'] = 'aob'
                    cd['AOB'] = req.media['aob'].upper()
                    cd['Offset'] = req.media['offset'].upper()
                    if 'Address' in cd:
                        del cd['Address']
                    if 'Value' in cd:
                        del cd['Value']
                    if 'Offsets' in cd:
                        del cd['Offsets']
            else:
                index = self.component_index
                if tp == 'address':
                    self.code_data[index] = {
                        "Name": "Code #{}".format(index),
                        "Type": "byte_4",
                        "Signed": False,
                        "Freeze": False,
                        "Source": "address",
                        "Address": req.media['address']
                    }
                elif tp == 'pointer':
                    self.code_data[index] = {
                        "Name": "Code #{}".format(index),
                        "Type": "byte_4",
                        "Signed": False,
                        "Freeze": False,
                        "Source": "pointer",
                        "Address": req.media['address'],
                        "Offsets": req.media['offsets'].upper()
                    }
                else:
                    self.code_data[index] = {
                        "Name": "Code #{}".format(index),
                        "Type": "byte_4",
                        "Signed": False,
                        "Freeze": False,
                        "Source": "aob",
                        "AOB": req.media['aob'].upper(),
                        "Offset": req.media['offset'].upper()
                    }
        if len(self.code_data) == 1:
            resp.media['file_data'] = self.code_data
            self.component_index = len(self.code_data)
        else:
            resp.media['index'] = index
            if 'index' not in req.media:
                resp.media['new_code'] = self.code_data[index]
                self.component_index += 1
            else:
                resp.media['edit_code'] = self.code_data[index]
        if not (self.freeze_thread and self.freeze_thread.is_alive()) and self.freeze_map:
            self.start_freezer()
        if not self.freeze_map:
            self.stop_freezer()
        if not (self.update_thread and self.update_thread.is_alive()):
            self.start_updater()
        resp.media['repeat'] = 1000

    def handle_aob_base_select(self, req: Request, resp: Response):
        with self.update_lock:
            index = int(req.media['index'])
            sel_index = int(req.media['select_index'])
            cd = self.code_data[index]
            cd['Selected'] = sel_index #int(req.media['selected'], 16)

    def handle_save(self, req: Request, resp: Response):
        file = req.media['file']
        write_data = copy.copy(self.code_data)
        try:
            for key, item in write_data.items():
                if 'Value' in item:
                    del item['Value']
                if 'Resolved' in item:
                    del item['Resolved']
                if 'Selected' in item:
                    del item['Selected']
            pt = self.directory.joinpath(file+'.codes')
            with open(pt, 'wt') as f:
                json.dump(list(write_data.values()), f, indent=4)
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
        resp.media['file_data'] = {}
        resp.media['file'] = self.loaded_file
        resp.media['files'] = self.get_code_files()




    def handle_name(self, req: Request, resp: Response):
        name = req.media['name']
        index = int(req.media['index'])
        if index not in self.code_data:
            raise CodelistException("Can't write code that isn't in the list")
        code = self.code_data[index]
        with self.update_lock:
            code['Name'] = name

    def handle_refresh(self, req: Request, resp: Response):
        index = int(req.media['index'])
        if index not in self.code_data:
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
            self.freeze_map = {}
            self.aob_map = {}
            return
        pt = self.directory.joinpath(req.media['file']+'.codes')
        if not pt.exists():
            raise CodelistException('Code file not found')
        try:
            with open(pt, 'rt') as ifile:
                self.code_data = {}
                codes = json.load(ifile)
                for i in range(0, len(codes)):
                    v = codes[i]
                    v['Value'] = {'Actual': None, 'Display': "??"}
                    v['Freeze'] = False
                    self.code_data[i] = v
                self.loaded_file = pt.stem
        except:
            raise CodelistException('Could not load code file')
        resp.media['file_data'] = self.code_data
        self.component_index = len(self.code_data)
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
        selected = code['Selected'] if 'Selected' in code and code['Selected'] else -1
        if aob.is_found():
            bases = self.utilities.compare_aob(aob)
            if not bases:
                aob.clear_bases()
            else:
                addrs = aob.get_bases()
                if 'Selected' not in code and len(addrs) > 0:
                    selected = 0
                elif 'Selected' in code:
                    selected = min(len(addrs)-1, code['Selected'])
                pos = addrs[selected]
                return self.get_read(code, pos + offset), [x+offset for x in aob.get_bases()], selected, selected >= 0

        if not aob.is_found():
            addrs = self.utilities.search_aob_all_memory(aob)
            if not addrs:
                aob.clear_bases()
            else:
                aob.set_bases(addrs)
                if 'Selected' not in code and len(addrs) > 0:
                    selected = 0
                elif 'Selected' in code:
                    selected = min(len(addrs)-1, code['Selected'])
                pos = addrs[selected]
                return self.get_read(code, pos + offset), [x+offset for x in aob.get_bases()], selected, selected >= 0
        return None, [], 0, 0

    def _update_process(self):
        while not self.update_event.is_set():
            with self.update_lock:
                self.result_map.clear()
                for key, code in self.code_data.items():
                    if code['Source'] == 'address':
                        try:
                            addr = self.base_converter.convert(self.mem(), code['Address'])
                            read = self.get_read(code, addr)
                            code['Resolved'] = addr if addr > 0xffff else 0
                        except (ProcessLookupError, PermissionError):
                            self.update_event.set()
                            read = None
                        except OSError:
                            read = None
                        except CodelistException:
                            read = None
                        self.result_map[key] = {'Value': {'Actual': read.value if read is not None else None, 'Display': str(read.value) if read is not None else '??'}}
                    elif code['Source'] == 'pointer':
                        offsets = [int(x.strip(), 16) for x in code['Offsets'].split(',')]
                        buf = ctypes.c_uint64()
                        try:
                            addr = self.base_converter.convert(self.mem(), code['Address'])
                            for offset in offsets:
                                self.mem().read_memory(addr, buf)
                                addr = buf.value+offset
                            read = self.get_read(code, addr)
                            code['Resolved'] = addr if addr > 0xffff else 0
                            if addr <= 0xffff:
                                addr = None
                        except (ProcessLookupError, PermissionError):
                            self.update_event.set()
                            read = None
                            addr = None
                        except OSError:
                            read = None
                            addr = None
                        except CodelistException:
                            read = None
                            addr = None
                        self.result_map[key] = {'Value': {'Actual': read.value if read is not None else None, 'Display': str(read.value) if read is not None else '??'},
                                                'Resolved': {'Actual': addr, 'Display': "{:X}".format(addr) if addr is not None else '????????'}}
                    else:
                        aob_str = code['AOB']
                        try:
                            if aob_str not in self.aob_map:
                                self.aob_map[aob_str] = AOB(code['Name'], aob_str)
                            read, addrs, selected, select_valid = self.read_aob_value(self.aob_map[aob_str], code)
                        except (ProcessLookupError, PermissionError):
                            self.update_event.set()
                            read, addrs, selected = (None, None, None)
                        except OSError:
                            read, addrs, selected = (None, None, None)
                        except AOBException:
                            read, addrs, selected = (None, None, None)
                        code['Selected'] = selected
                        self.result_map[key] = {'Value': {'Actual': read.value if read is not None else None, 'Display': str(read.value) if read is not None else '??'},
                                                'Addresses': {'Actual': addrs, 'Display': ["{:X}".format(x) for x in addrs] if addrs is not None else []},
                                                'Selected': selected}
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
            elif code['Type'] == 'byte_8':
                if value > 0x7FFFFFFFFFFFFFFF:
                    code['Signed'] = False
                value = max(-0x7FFFFFFFFFFFFFFF, min(0xFFFFFFFFFFFFFFFF, value))
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
        self.freeze_map = {}
        self.aob_map = {}
        self.update_thread = Thread(target=self._update_process)
        self.update_event = Event()
        self.update_thread.start()

    def stop_updater(self):
        if self.update_thread and self.update_thread.is_alive():
            self.update_event.set()
            self.update_thread.join()

    def get_results(self):
        res = self.result_map.copy()
        return res

    def _freeze_process(self):
        while not self.freeze_event.is_set():
            with self.update_lock:
                try:
                    for key, value in self.freeze_map.items():
                        addrs = self.get_addresses(value['code'])
                        for addr in addrs:
                            self.mem().write_memory(addr, value['value'])
                except (ProcessLookupError, PermissionError) as e:
                    self.freeze_map.clear()
                    self.freeze_event.set()
            self.freeze_event.wait(0.5)

    def get_addresses(self, code):
        address_list = []
        if code['Source'] == 'address':
            if 'Resolved' in code and code['Resolved'] > 0:
                address_list.append(code['Resolved'])
        elif code['Source'] == 'pointer':
            if 'Resolved' in code and code['Resolved'] > 0:
                address_list.append(code['Resolved'])
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