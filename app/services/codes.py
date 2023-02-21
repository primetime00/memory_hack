import base64
import copy
import ctypes
import json
import os
import random
from io import BytesIO
from pathlib import Path
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
from app.helpers.process import BaseConvert, BaseConvertException, get_address_path, get_path_address
from app.script_common.aob import AOB
from app.script_common.utilities import ScriptUtilities
from app.version import __version__

ctypes_buffer_t = Union[ctypes._SimpleCData, ctypes.Array, ctypes.Structure, ctypes.Union]


class CodeList(MemoryHandler):
    directory = codes_directory
    _FILE_VERSION = __version__
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
            "CODELIST_AOB_SELECT": self.handle_aob_base_select,
            "CODELIST_UPLOAD": self.handle_upload,
            "CODELIST_REBASE_CODE": self.handle_rebase,
        }
        self.update_thread: Thread = None
        self.update_event: Event = None
        self.update_lock: Lock = Lock()

        self.freeze_thread: Thread = None
        self.freeze_event: Event = None

        self.aob_thread: Thread = None
        self.aob_event: Event = None
        self.aob_searcher: ScriptUtilities = None

        self.code_data: dict = None
        self.loaded_file = "_null"
        self.file_version = CodeList._FILE_VERSION
        self.aob_map: dict[str, AOB] = {}
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
        self.stop_aob()
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
        resp.media['repeat'] = 400 if self.code_data else 0
        resp.media['file'] = self.loaded_file
        if self.code_data:
            resp.media['file_data'] = self.code_data

    def handle_status(self, req: Request, resp: Response):
        resp.media['repeat'] = 400 if self.code_data else 0
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
        resp.media['frozen'] = {'index': index}
        if index not in self.code_data:
            raise CodelistException("Can't write code that isn't in the list")
        with self.update_lock:
            value = copy.copy(self.get_results()[index])
            if value['Value']['Actual'] is None:
                resp.media['frozen']['set'] = False
                return
            code = self.code_data[index]
            code['Freeze'] = frozen
            if frozen:
                dt = memory_utils.typeToCType[(code['Type'], code['Signed'])]
                self.freeze_map[index] = {'value': dt(value['Value']['Actual']), 'index': index, 'code': code}
                resp.media['frozen']['set'] = True
            else:
                if index in self.freeze_map:
                    del self.freeze_map[index]
                resp.media['frozen']['set'] = False
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
        self.process_delete(self.code_data[index], index)
        try:
            self.component_index = max(list(self.code_data.keys()))+1
        except ValueError:
            self.component_index = 0
        if index in self.result_map:
            del self.result_map[index]
        resp.media['remove_index'] = index

    def handle_add_code(self, req: Request, resp: Response):
        tp = req.media['type']
        if not self.code_data:
            self.code_data = {}
        if tp == 'aob_from_address':
            aob = self.code_data[int(req.media['index'])]['AOB']
            addr = int(req.media['address'], 16)
            bases = self.aob_map[aob].get_bases()
            if not bases:
                return
            min_item = 0xFF
            min_distance = 0x7FFFFFFFFFFFFFFF
            for i in range(0, len(bases)):
                cr = bases[i]
                dist = abs(addr - cr)
                if dist < min_distance:
                    min_distance = dist
                    min_item = i
            offset = bases[min_item] - addr
            req.media['aob'] = aob
            req.media['offset'] = '{:X}'.format(-offset)
            req.media['address'] = 0
            req.media['type'] = 'aob'
            del req.media['index']
            tp = 'aob'
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
                self.process_add(cd)
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
                self.process_add(self.code_data[index])
        if len(self.code_data) == 1:
            resp.media['file_data'] = self.code_data
            self.component_index = max(list(self.code_data.keys()))+1
        else:
            resp.media['index'] = index
            if 'index' not in req.media:
                resp.media['new_code'] = self.code_data[index]
                self.component_index = max(list(self.code_data.keys()))+1
            else:
                resp.media['edit_code'] = self.code_data[index]
        if not (self.freeze_thread and self.freeze_thread.is_alive()) and self.freeze_map:
            self.start_freezer()
        if not self.freeze_map:
            self.stop_freezer()
        if not (self.update_thread and self.update_thread.is_alive()):
            self.start_updater()
        if not (self.aob_thread and self.aob_thread.is_alive()):
            self.start_aob()

        resp.media['repeat'] = 400

    def handle_rebase(self, req: Request, resp: Response):
        tp = req.media['type']
        with self.update_lock:
            if 'index' in req.media:
                index = int(req.media['index'])
                cd = self.code_data[index]
                if tp != cd['Source']:
                    return
                if index in self.result_map:
                    del self.result_map[index]
                if index in self.freeze_map:
                    del self.freeze_map[index]
                    cd['Freeze'] = False
                if tp == 'address':
                    old_address = cd['Address']
                    new_address = req.media['address']
                    diff = int(new_address, 16) - int(old_address, 16)
                    cd['Address'] = req.media['address']
                    cd['Freeze'] = False
                    edit_list = [(index, cd)]
                    for (_index, current_code) in [(_index, x) for (_index, x) in self.code_data.items() if x['Source'] == tp and x != cd]:
                        current_code['Address'] = '{:X}'.format(int(current_code['Address'], 16) + diff)
                        current_code['Freeze'] = False
                        if _index in self.freeze_map:
                            del self.freeze_map[_index]
                        if _index in self.result_map:
                            del self.result_map[_index]
                        edit_list.append((_index, current_code))
                    resp.media['changes'] = edit_list
                elif tp == 'pointer':
                    old_address = cd['Address']
                    old_offsets = cd['Offsets'].split(',')
                    new_offsets = req.media['offsets'].split(',')
                    diff = int(new_offsets[-1], 16) - int(old_offsets[-1], 16)
                    cd['Address'] = req.media['address']
                    cd['Offsets'] = req.media['offsets'].upper()
                    cd['Freeze'] = False
                    edit_list = [(index, cd)]
                    for (_index, current_code) in [(_index, x) for (_index, x) in self.code_data.items() if x['Source'] == tp and x != cd and x['Address'] == old_address]:
                        if [int(x, 16) for x in current_code['Offsets'].split(',')[0:-1]] != [int(x, 16) for x in req.media['offsets'].split(',')[0:-1]]:
                            continue
                        current_code['Address'] = req.media['address']
                        offsets = [int(x, 16) for x in current_code['Offsets'].split(',')]
                        offsets[-1] = offsets[-1] + diff
                        current_code['Offsets'] = ', '.join(['{:X}'.format(x) for x in offsets])
                        current_code['Resolved'] = '????????'
                        current_code['Freeze'] = False
                        if _index in self.freeze_map:
                            del self.freeze_map[_index]
                        if _index in self.result_map:
                            del self.result_map[_index]
                        edit_list.append((_index, current_code))
                    resp.media['changes'] = edit_list
                else:
                    old_aob = cd['AOB']
                    old_offset = int(cd['Offset'], 16)
                    new_offset = int(req.media['offset'], 16)
                    diff = new_offset - old_offset
                    cd['AOB'] = req.media['aob'].upper()
                    cd['Offset'] = req.media['offset'].upper()
                    cd['Freeze'] = False
                    edit_list = [(index, cd)]
                    for (_index, current_code) in [(_index, x) for (_index, x) in self.code_data.items() if x['Source'] == tp and x != cd and x['AOB'] == old_aob]:
                        current_code['AOB'] = req.media['aob'].upper()
                        current_code['Offset'] = '{:X}'.format(int(current_code['Offset'], 16) + diff)
                        current_code['Freeze'] = False
                        if _index in self.freeze_map:
                            del self.freeze_map[_index]
                        if _index in self.result_map:
                            del self.result_map[_index]
                        edit_list.append((_index, current_code))
                    resp.media['changes'] = edit_list
                    if old_aob in self.aob_map:
                        del self.aob_map[old_aob]
                    self.process_add(cd)
        resp.media['repeat'] = 400

    def handle_aob_base_select(self, req: Request, resp: Response):
        with self.update_lock:
            index = int(req.media['index'])
            sel_index = int(req.media['select_index'])
            cd = self.code_data[index]
            cd['Selected'] = sel_index #int(req.media['selected'], 16)

    def handle_save(self, req: Request, resp: Response):
        file = req.media['file']
        try:
            dt = self.dump_codelist()
            pt = self.directory.joinpath(file+'.codes')
            pt.write_text(dt)
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

    def get_stream(self) -> BytesIO:
        dt = self.dump_codelist()
        return BytesIO(dt.encode())

    def handle_download(self, req: Request, resp: Response):
        name = req.params['name']
        resp.downloadable_as = name+'.codes'
        resp.content_type = 'application/octet-stream'
        resp.stream = self.get_stream()
        resp.status = 200

    def handle_upload(self, req: Request, resp: Response):
        name: str = req.media['name'].strip()
        data = base64.b64decode(req.media['data'].split(',')[1])
        pt = Path(name)
        filename: str = pt.stem
        name_list = [item.casefold() for item in self.get_code_files()]
        index = 0
        proposed_filename = filename
        while proposed_filename.casefold() in name_list:
            index += 1
            proposed_filename = "{}-{:03d}".format(filename, index)
        with open(Path(CodeList.directory.joinpath(proposed_filename+'.codes')), 'wt') as f:
            f.write(data.decode())
        resp.media['message'] = 'Upload complete'
        req.media['file'] = proposed_filename
        self.handle_load(req, resp)
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
        self.stop_freezer()
        self.stop_updater()
        self.stop_aob()
        if req.media['file'] == '_null':
            self.code_data = None
            self.loaded_file = "_null"
            resp.media['file_data'] = self.code_data
            resp.media['file'] = self.loaded_file
            self.freeze_map = {}
            self.aob_map.clear()
            return
        pt = self.directory.joinpath(req.media['file']+'.codes')
        if not pt.exists():
            raise CodelistException('Code file not found')
        try:
            with open(pt, 'rt') as ifile:
                self.code_data = {}
                codes = json.load(ifile)
                if type(codes) is dict:
                    self.file_version = codes.get('version', CodeList._FILE_VERSION)
                    codes = codes.get('codes', [])
                else:
                    self.file_version = CodeList._FILE_VERSION
                for i in range(0, len(codes)):
                    v = codes[i]
                    v['Value'] = {'Actual': None, 'Display': "??"}
                    v['Freeze'] = False
                    self.code_data[i] = v
                    self.file_version = CodeList._FILE_VERSION
                    self.process_add(v)
                self.loaded_file = pt.stem
        except:
            raise CodelistException('Could not load code file')
        resp.media['file_data'] = self.code_data
        self.component_index = max(list(self.code_data.keys()))+1
        resp.media['file'] = self.loaded_file
        resp.media['repeat'] = 400
        self.start_updater()
        self.start_aob()

    def dump_codelist(self):
        write_data = copy.copy(self.code_data)
        for key, item in write_data.items():
            if 'Value' in item:
                del item['Value']
            if 'Resolved' in item:
                del item['Resolved']
            if 'Selected' in item:
                del item['Selected']
        for c in write_data.values():
            if c['Source'] == 'address':
                if ':' not in c['Address']:
                    addr = int(c['Address'], 16)
                    path = get_address_path(self.mem(), addr)
                    if path:
                        c['Address'] = path
            elif c['Source'] == 'aob':
                aob = c['AOB'].split(' ')
                aob_data = []
                for a in aob:
                    if a == '??':
                        aob_data.append('??')
                    else:
                        aob_data.append('{:02X}'.format(int(a, 16)))
                c['AOB'] = ' '.join(aob_data)
        file_data = {'version': CodeList._FILE_VERSION,
                     'codes': list(write_data.values())}
        return json.dumps(file_data, indent=4)

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
        pt = list(self.directory.glob('*.codes'))
        st = [(x.stem, x.stat().st_mtime) for x in pt]
        return [y[0] for y in sorted(st, key=lambda x: x[1], reverse=False)]


    def read_aob_value(self, aob: AOB, code):
        offset = int(code['Offset'], 16)
        selected = code['Selected'] if 'Selected' in code and code['Selected'] else -1
        if aob.is_found():
            addrs = aob.get_bases()
            if 'Selected' not in code and len(addrs) > 0:
                selected = 0
            elif 'Selected' in code:
                selected = min(len(addrs)-1, code['Selected'])
            pos = addrs[selected]
            return self.get_read(code, pos + offset), [x+offset for x in aob.get_bases()], selected, selected >= 0
        return None, [], 0, 0


    def process_add(self, code):
        if code['Source'] == 'aob':
            if code['AOB'] not in self.aob_map:
                self.aob_map[code['AOB']] = AOB('', code['AOB'])
        if code['Source'] == 'address':
            if ':' in code['Address']:
                addr = get_path_address(self.mem(), code['Address'])
                code['Address'] = '{:X}'.format(addr)


    def process_delete(self, code, index):
        if code['Source'] == 'aob':
            aob_str = code['AOB']
            del self.code_data[index]
            if aob_str not in [x['AOB'] for x in self.code_data.values() if x['Source'] == 'aob']:
                del self.aob_map[aob_str]
        else:
            del self.code_data[index]

    def update_aobs(self):
        for aob in self.aob_map.values():
            if aob.is_found():
                bases = self.utilities.compare_aob(aob)
                aob.set_bases(bases)
            #if not aob.is_found() and aob.get_last_searched() > random.randint(8, 12):
            else:
                bases = self.utilities.search_aob_all_memory(aob)
                aob.set_bases(bases)
    def _update_process(self):
        while not self.update_event.is_set():
            with self.update_lock:
                self.result_map.clear()
                if self.aob_map:
                    self.update_aobs()
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
                        except BaseConvertException:
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
                        except BaseConvertException:
                            read = None
                            addr = None
                        self.result_map[key] = {'Value': {'Actual': read.value if read is not None else None, 'Display': str(read.value) if read is not None else '??'},
                                                'Resolved': {'Actual': addr, 'Display': "{:X}".format(addr) if addr is not None else '????????'}}
                    else:
                        aob_str = code['AOB']
                        try:
                            read, addrs, selected, select_valid = self.read_aob_value(self.aob_map[aob_str], code)
                        except (ProcessLookupError, PermissionError):
                            self.update_event.set()
                            read, addrs, selected = (None, None, None)
                        except OSError:
                            read, addrs, selected = (None, None, None)
                        except AOBException:
                            read, addrs, selected = (None, None, None)
                        except Exception: #somethiung else happened
                            return
                        if selected is None:
                            if 'Selected' in code:
                                del code['Selected']
                        else:
                            code['Selected'] = selected
                        self.result_map[key] = {'Value': {'Actual': read.value if read is not None else None, 'Display': str(read.value) if read is not None else '??'},
                                                'Addresses': {'Actual': addrs, 'Display': ["{:X}".format(x) for x in addrs] if addrs is not None else []},
                                                'LastAddresses': self.aob_map[aob_str].get_last_found_bases(),
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
            self.freeze_event.wait(0.25)

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

    def start_aob(self):
        self.aob_thread = Thread(target=self._aob_process)
        self.aob_event = Event()
        self.aob_searcher = ScriptUtilities(self.mem(), "aob_searcher", multi=False)
        self.aob_thread.start()

    def stop_aob(self):
        if self.aob_thread and self.aob_thread.is_alive():
            self.aob_event.set()
            self.aob_searcher.cancel()
            self.aob_thread.join()

    def _aob_process(self):
        self.aob_searcher.create_searcher()
        base_list = {}
        while not self.aob_event.is_set():
            base_list.clear()
            if self.aob_map:
                for aob in self.aob_map.values():
                    bases = self.aob_searcher.search_aob_all_memory(aob)
                    base_list[aob] = bases
                with self.update_lock:
                    for aob, bases in base_list.items():
                        aob.set_bases(bases)
            self.aob_event.wait(15)

