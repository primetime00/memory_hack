import base64
import ctypes
import logging
import os
from io import BytesIO
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import List

from falcon import Request, Response, MEDIA_JSON
from mem_edit import Process

from app.helpers.aob_file import AOBFile
from app.helpers.aob_utils import AOBUtilities
from app.helpers.data_store import DataStore
from app.helpers.directory_utils import aob_directory
from app.helpers.dyn_html import DynamicHTML
from app.helpers.exceptions import AOBException, BreakException
from app.helpers.memory_handler import MemoryHandler
from app.helpers.process import BaseConvert
from app.helpers.progress import Progress
from app.helpers.search_results import SearchResults
from app.search.searcher_multi import SearcherMulti


class AOB(MemoryHandler):
    directory = aob_directory
    FLOW_START = 0
    FLOW_SEARCHING = 1
    FLOW_RESULTS = 2
    FLOW_NO_RESULTS = 3
    FLOW_WORKING = 5
    FLOW_INITIAL_COMPLETE = 6
    def __init__(self):
        super().__init__('aob')
        self.handle_map = {
            "AOB_INITIALIZE": self.handle_initialization,
            "AOB_SELECT": self.handle_select,
            "AOB_RESET": self.handle_reset,
            "AOB_SEARCH": self.handle_search,
            "AOB_DOWNLOAD": self.handle_download,
            "AOB_UPLOAD": self.handle_upload,
            "AOB_STATUS": self.handle_initialization,
            "AOB_COUNT": self.handle_count,
            "AOB_DELETE": self.handle_delete,
            "AOB_DELETE_FILE": self.handle_delete_file,
        }
        self.flow = self.FLOW_START
        self.previous_state = {'flow': self.FLOW_START, 'name': ""}

        self.aob_work_thread: AOB.AOBWorkThread = None
        self.count_thread: Thread = None
        self.count_queue: Queue = Queue()
        self.current_name = ''
        self.set_current_name('')
        self.current_search_type = 'address'
        self.base_converter = BaseConvert()
        self.current_address = 0
        self.current_range = 65536
        self.current_value = None
        self.current_value_size = None
        self.searcher: SearcherMulti = None
        self.aob_results: List[dict] = []
        self.aob_file: AOBFile = AOBFile()

        if not AOB.directory.exists():
            os.makedirs(AOB.directory, exist_ok=True)

        self.reset()
        #self.delete_memory()

    def kill(self):
        if self.aob_work_thread and self.aob_work_thread.is_alive():
            DataStore().get_operation_control().control_break()
            self.aob_work_thread.join()

    def set(self, data):
        self.searcher = SearcherMulti(self.mem(), write_only=True, directory=AOB.directory, results=SearchResults('aob', db_path=AOB.directory.joinpath('aob_count.db')))

    def release(self):
        self.reset()

    def process_error(self, msg: str):
        self.reset()

    def reset(self):
        if self.aob_work_thread and self.aob_work_thread.is_alive():
            DataStore().get_operation_control().control_break()
            self.aob_work_thread.join()
        self.flow = self.FLOW_START
        self.set_current_name('')
        self.current_search_type = 'address'
        self.current_address = 0
        self.current_range = 0
        self.current_value = None
        self.current_value_size = None
        self.aob_work_thread: AOB.AOBWorkThread = None


    def html_main(self):
        return DynamicHTML('resources/aob.html', 2).get_html()

    def set_current_name(self, _name):
        self.current_name = _name
    def delete_memory(self):
        for x in AOB.directory.glob('*.mem'):
            os.unlink(x)

    def get_search_progress(self):
        if not (self.aob_work_thread and self.aob_work_thread.is_alive()):
            return 0
        return self.aob_work_thread.get_progress()

    def handle_reset(self, req: Request, resp: Response):
        if self.aob_work_thread and self.aob_work_thread.is_alive():
            self.aob_work_thread.kill()
            self.aob_work_thread.join()
        self.flow = self.previous_state['flow']
        self.set_current_name(self.previous_state['name'])
        resp.media['repeat'] = 100
        self.aob_work_thread: AOB.AOBWorkThread = None


    def handle_download(self, req: Request, resp: Response):
        name = req.params['name']
        resp.downloadable_as = name+'.aob'
        resp.content_type = 'application/octet-stream'
        resp.stream = self.aob_file.get_stream(filename=name+'.aob')
        resp.status = 200

    def handle_upload(self, req: Request, resp: Response):
        name: str = req.media['name'].strip()
        data = base64.b64decode(req.media['data'].split(',')[1])
        pt = Path(name)
        filename: str = pt.stem
        name_list = [item.casefold() for item in self.get_aob_list()]
        index = 0
        proposed_filename = filename
        while proposed_filename.casefold() in name_list:
            index += 1
            proposed_filename = "{}-{:03d}".format(filename, index)
        self.aob_file.set_name(proposed_filename)
        try:
            self.aob_file.read_stream(BytesIO(data))
            self.current_name = proposed_filename
            self.process_aob_file(resp, update_results=True)
            resp.media['name'] = proposed_filename
            resp.media['range'] = self.aob_file.get_range()
            self.aob_file.write()
            resp.media['message'] = 'Upload complete'
        except AOBException as e:
            resp.media['name'] = self.current_name
            resp.media['error'] = 'Upload failed: {}'.format(e.get_message())
        resp.media['names'] = self.get_aob_list()

    def handle_search(self, req: Request, resp: Response):
        name = req.media["name"]
        search_type = req.media["search_type"]
        search_range = req.media["range"]
        address_value = req.media["address_value"]
        value_size = req.media["value_size"]
        self.aob_file.set_name(name)
        self.set_current_name(name)
        try:
            self.aob_work_thread = AOB.AOBWorkThread(self.aob_file, self.mem(), search_type, address_value, search_range, value_size, self.searcher)
        except ValueError as e:
            resp.media['error'] = 'Could not start: {}'.format(e)
            return
        self.previous_state['flow'] = self.flow
        self.previous_state['name'] = name
        self.flow = self.FLOW_WORKING
        self.current_search_type = search_type
        if search_type == 'value':
            self.current_value = req.media['address_value']
        else:
            self.current_address = req.media['address_value']
        self.current_value_size = value_size
        self.aob_work_thread.start()
        resp.media['repeat'] = 1000
        resp.media['progress'] = self.get_search_progress()

    def handle_initialization(self, req: Request, resp: Response):
        if self.flow == self.FLOW_START:
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type
            resp.media['value'] = self.current_value
            resp.media['range'] = 65536 if self.current_range <= 0  else self.current_range
            resp.media['valid_types'] = ['address']
            if self.current_name in self.get_aob_list():
                resp.media['valid_types'].append('value')
        elif self.flow == self.FLOW_WORKING:
            if self.aob_work_thread and not self.aob_work_thread.is_alive():
                self.process_aob_file(resp, update_results=True)
                resp.media['name'] = self.current_name
                resp.media['names'] = self.get_aob_list()
                resp.media['type'] = self.current_search_type
            else:
                resp.media['repeat'] = 1000
                resp.media['progress'] = self.get_search_progress()
        elif self.flow == self.FLOW_RESULTS:
            self.process_aob_file(resp)
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type
            if self.count_thread and self.count_thread.is_alive():
                resp.media['repeat'] = 400
            while not self.count_queue.empty():
                cc = self.count_queue.get()
                self.aob_results[cc[0]]['count'] = cc[1]
        elif self.flow == self.FLOW_INITIAL_COMPLETE:
            self.process_aob_file(resp)
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type


    def handle_select(self, req: Request, resp: Response):
        name = req.media['name']
        if name == '_null':
            name = ""
        self.set_current_name(name)
        self.aob_file.set_name(name)
        if self.current_name in self.get_aob_list():
            self.process_aob_file(resp, update_results=True)
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type
        else:
            self.flow = self.FLOW_START
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type
            resp.media['valid_types'] = ['address']

    def handle_count(self, req: Request, resp: Response):
        aob = self.aob_results[int(req.media['index'])]
        resp.media['repeat'] = 400
        self.count_thread = Thread(target=self._count_thread, args=(aob, int(req.media['index']),))
        self.count_thread.start()

    def handle_delete(self, req: Request, resp: Response):
        index = int(req.media['index'])
        self.aob_file.remove_index(index)
        self.aob_file.write()
        self.aob_results.pop(index)
        resp.media['repeat'] = 100

    def handle_delete_file(self, req: Request, resp: Response):
        fname = req.media['file']
        for f in AOB.directory.glob('{}.*'.format(fname)):
            f.unlink(missing_ok=True)
        self.set_current_name("")
        self.flow = self.FLOW_START
        resp.media['name'] = self.current_name
        resp.media['names'] = self.get_aob_list()
        resp.media['type'] = self.current_search_type
        resp.media['valid_types'] = ['address']


    def _count_thread(self, aob, index):
        aob_str: str = aob['aob']
        self.searcher.set_search_size('array')
        self.searcher.search_memory_value(aob_str)
        self.count_queue.put((index, len(self.searcher.results)))


    def process_aob_file(self, resp: Response, update_results=False):
        resp.media['is_initial_search'] = False
        resp.media['is_final'] = False
        if self.aob_file.get_state() == AOBFile.FILE_STATE_HAS_RESULTS:
            self.flow = self.FLOW_RESULTS
            resp.media['number_of_results'] = self.aob_file.count_aob_results()
            addr = self.base_converter.convert(self.mem(), str(self.current_address))
            if self.current_search_type == 'address' and (not addr or addr <= 0xFFFF):
                self.current_address = "0"
            resp.media['value'] = self.current_value if self.current_search_type == 'value' else self.current_address
            resp.media['type'] = self.current_search_type
            resp.media['size'] = self.current_value_size
            resp.media['valid_types'] = ['address']
            resp.media['valid_types'].append('value')
            if update_results:
                self.aob_results = self.aob_file.get_results()
                resp.media['results'] = self.aob_results
            else:
                resp.media['results'] = self.aob_results
        elif self.aob_file.get_state() == AOBFile.FILE_STATE_NOT_EXIST:
            self.flow = self.FLOW_START
            resp.media['range'] = self.aob_file.get_range()
        elif self.aob_file.get_state() == AOBFile.FILE_STATE_INITIAL_RESULTS:
            self.flow = self.FLOW_INITIAL_COMPLETE
            resp.media['is_initial_search'] = True
        elif self.aob_file.get_state() == AOBFile.FILE_STATE_NO_RESULTS:
            self.flow = self.FLOW_NO_RESULTS
            resp.media['is_final'] = True
            resp.media['range'] = self.aob_file.get_range()

    def process(self, req: Request, resp: Response):
        resp.media = {}
        command = req.media['command']
        assert (command in self.handle_map)
        resp.content_type = MEDIA_JSON
        try:
            self.handle_map[command](req, resp)
        except AOBException as e:
            resp.media['error'] = e.get_message()
        finally:
            resp.media['flow'] = self.flow

    def get_aob_list(self):
        return [x.stem for x in AOB.directory.glob('*.aob')]

    class AOBWorkThread(Thread):
        smallest_run = 5
        consecutive_zeros = 5

        def __init__(self, _aob_file: AOBFile, _memory, _type=None, _address_value=None, _range=None, _size=None, searcher=None):
            super().__init__(target=self.process)
            self.aob_file = _aob_file
            self.memory: Process = _memory
            self.base_converter = BaseConvert()
            self.current_name = self.aob_file.get_name()
            self.current_address = self.base_converter.convert(_memory, _address_value) if _type == 'address' else 0
            self.current_range = int(_range) if _range else 0
            if self.current_range <= 0:
                raise AOBException('Range must be greater than 0.')
            self.current_value = str(_address_value) if _type == 'value' else ""
            self.current_size = _size
            self.is_value = _type == 'value'
            self.current_range = int(_range) if _range else 0
            if self.current_range % 2 != 0:
                self.current_range += 1
            self.progress = Progress()
            self.error = ""
            self.stop = False
            self.searcher = searcher
            self.operation_control = DataStore().get_operation_control()


        def get_file(self):
            return self.aob_file

        def kill(self):
            self.stop = True

        def get_progress(self):
            return self.progress.get_progress()

        def is_initial_needed(self):
            if not self.aob_file.exists():
                return True
            else:
                if not self.aob_file.is_final() and not self.aob_file.is_initial():
                    return True
                return False

        def process_address_run(self):
            if self.aob_file.get_state() == AOBFile.FILE_STATE_NOT_EXIST:
                # start needs to be an address
                self.progress.add_constraint(0, 100, 1.0)
                au = AOBUtilities(self.memory, DataStore().get_operation_control(), self.progress)
                start, end, self.current_range = au.calculate_range(self.current_address, self.current_range)
                if start == -1:  # error with range
                    self.error = "Invalid address for this process."
                    return
                self.progress.increment(30)
                try:
                    data = self.memory.read_memory(start, (ctypes.c_ubyte * (end - start))())
                    self.aob_file.add_data(data)
                except OSError:
                    self.error = "Invalid region to scan."
                    return
                self.progress.increment(40)
                self.aob_file.set_process(DataStore().get_process('aob'))
                self.aob_file.set_range(self.current_range)
                self.aob_file.set_address_offset(self.current_address - start)
                self.aob_file.set_length(end-start)
                self.aob_file.write()
                self.progress.mark()
            elif self.aob_file.get_state() == AOBFile.FILE_STATE_INITIAL_RESULTS or self.aob_file.get_state() == AOBFile.FILE_STATE_HAS_RESULTS:
                self.aob_address_search()
                self.aob_file.write()

        def process_value_run(self):
            if not self.aob_file.exists():
                logging.error("Trying to do a value search without an .aob file!")
                return
            try:
                self.aob_value_search()
            except AOBException as e:
                self.error = 'Search Failed: {}'.format(e.get_message())

        def process(self):
            try:
                if not self.is_value:
                    self.process_address_run()
                else:
                    self.process_value_run()
            except BreakException:
                pass

        def aob_value_search(self):
            new_data = []
            self.searcher.set_search_size('array')
            data = self.aob_file.get_data_list()[-1]
            self.progress.add_constraint(0, len(data), 1.0)
            if self.current_value.strip().startswith('-'):
                sz_map = {'byte_1': ctypes.c_int, 'byte_2': ctypes.c_int16, 'byte_4': ctypes.c_int32, 'byte_8': ctypes.c_int64}
            else:
                sz_map = {'byte_1': ctypes.c_uint, 'byte_2': ctypes.c_uint16, 'byte_4': ctypes.c_uint32, 'byte_8': ctypes.c_uint64}
            read = sz_map[self.current_size]()
            for i in range(0, len(data)):
                found = False
                aob = data[i]
                self.searcher.search_memory_value(aob['aob_string'])
                self.progress.increment(1)
                if self.stop:
                    self.stop = False
                    return -1
                with self.searcher.results.db() as conn:
                    for res in self.searcher.results.get_results(connection=conn):
                        address = res[0]
                        try:
                            self.memory.read_memory(address - aob['offset_from_address'], read)
                            if read.value == int(self.current_value):
                                found = True
                                break
                        except OSError:
                            continue
                if found:
                    d = data[i].copy()
                    d['index'] += 1
                    new_data.append(d)
            self.progress.mark()
            self.aob_file.add_data_list_item(new_data)
            self.aob_file.write()
            return len(new_data)

        def aob_address_search(self):
            self.progress.add_constraint(0, 1, 0.1)
            au = AOBUtilities(self.memory, DataStore().get_operation_control(), self.progress)
            heap_start, heap_end = au.find_heap_data(self.memory, self.current_address)
            start = self.current_address - self.aob_file.get_address_offset()
            end = start+self.aob_file.get_length()
            start_diff = heap_start - start
            end_diff = heap_end - end
            real_start = max(start, heap_start)
            real_end = min(end, heap_end)
            try:
                new_data = (ctypes.c_ubyte * (end - start))()
                if start_diff > 0 or end_diff < 0:
                    new_data_address = ctypes.addressof(new_data)
                    real_data = (ctypes.c_ubyte * (real_end - real_start)).from_address(new_data_address+start_diff)
                    self.memory.read_memory(real_start, real_data)
                else:
                    new_data = self.memory.read_memory(start, new_data)
            except OSError:
                self.progress.mark()
                return 0
            self.progress.mark()
            self.aob_file.add_data(new_data)
            self.aob_file.write()
            return self.aob_file.count_aob_results()

