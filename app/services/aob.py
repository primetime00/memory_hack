import ctypes
import logging
import os
from io import StringIO
from pathlib import Path
from queue import Queue
from threading import Thread

from falcon import Request, Response, MEDIA_JSON
from mem_edit import Process

from app.helpers.aob_file import AOBFile
from app.helpers.aob_utils import AOBUtilities
from app.helpers.aob_walk import AOBWalk
from app.helpers.data_store import DataStore
from app.helpers.directory_utils import aob_directory
from app.helpers.dyn_html import DynamicHTML
from app.helpers.exceptions import AOBException, BreakException
from app.helpers.memory_handler import MemoryHandler
from app.helpers.memory_utils import value_to_hex, bytes_to_aobstr
from app.helpers.process import BaseConvert
from app.helpers.progress import Progress
from app.search.searcher_multi import SearcherMulti
from app.helpers.search_results import SearchResults


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
        self.aob_results: list = []

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
            DataStore().get_operation_control().control_break()
            self.aob_work_thread.join()
        self.flow = self.previous_state['flow']
        self.set_current_name(self.previous_state['name'])
        resp.media['repeat'] = 100
        self.aob_work_thread: AOB.AOBWorkThread = None


    def handle_download(self, req: Request, resp: Response):
        name = req.params['name']
        resp.downloadable_as = name+'.aob'
        resp.content_type = 'application/octet-stream'
        resp.stream = AOBFile(directory=AOB.directory).get_stream(filename=name+'.aob')
        resp.status = 200

    def handle_upload(self, req: Request, resp: Response):
        name: str = req.media['name'].strip()
        data: str = req.media['data']
        pt = Path(name)
        filename: str = pt.stem
        name_list = [item.casefold() for item in self.get_aob_list()]
        index = 0
        proposed_filename = filename
        while proposed_filename.casefold() in name_list:
            index += 1
            proposed_filename = "{}-{:03d}".format(filename, index)
        aob_file = AOBFile(filename=proposed_filename+'.aob')
        try:
            aob_file.read_stream(StringIO(data))
            self.current_name = proposed_filename
            self.process_selected_file(resp, aob_file)
            self.aob_results = aob_file.get_results()
            resp.media['name'] = proposed_filename
            resp.media['range'] = aob_file.get_range()
            aob_file.write()
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
        self.set_current_name(name)
        try:
            self.aob_work_thread = AOB.AOBWorkThread(self.mem(), name, search_type, address_value, search_range, value_size)
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
                ab_file = self.aob_work_thread.get_file()
                self.process_selected_file(resp, ab_file)
                self.aob_results = ab_file.get_results()
                resp.media['name'] = self.current_name
                resp.media['names'] = self.get_aob_list()
                resp.media['type'] = self.current_search_type
            else:
                resp.media['repeat'] = 1000
                resp.media['progress'] = self.get_search_progress()
        elif self.flow == self.FLOW_RESULTS:
            ab_file = AOBFile(directory=AOB.directory, filename=self.current_name+'.aob')
            self.process_selected_file(resp, ab_file)
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type
            if self.count_thread and self.count_thread.is_alive():
                resp.media['repeat'] = 400
            while not self.count_queue.empty():
                cc = self.count_queue.get()
                self.aob_results[cc[0]]['count'] = cc[1]
            resp.media['results'] = self.aob_results
        elif self.flow == self.FLOW_INITIAL_COMPLETE:
            ab_file = AOBFile(directory=AOB.directory, filename=self.current_name+'.aob')
            self.process_selected_file(resp, ab_file)
            resp.media['name'] = self.current_name
            resp.media['names'] = self.get_aob_list()
            resp.media['type'] = self.current_search_type


    def handle_select(self, req: Request, resp: Response):
        name = req.media['name']
        if name == '_null':
            name = ""
        self.set_current_name(name)
        if self.current_name in self.get_aob_list():
            ab_file = AOBFile(directory=AOB.directory, filename=self.current_name+'.aob')
            self.process_selected_file(resp, ab_file)
            self.aob_results = ab_file.get_results()
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
        ab_file = AOBFile(directory=AOB.directory, filename=self.current_name + '.aob')
        aob = ab_file.get_aob_list()[int(req.media['index'])]
        resp.media['repeat'] = 400
        self.count_thread = Thread(target=self._count_thread, args=(aob, int(req.media['index']),))
        self.count_thread.start()

    def handle_delete(self, req: Request, resp: Response):
        index = int(req.media['index'])
        ab_file = AOBFile(directory=AOB.directory, filename=self.current_name + '.aob')
        ab_file.remove_index(index)
        ab_file.write()
        self.aob_results.pop(index)
        resp.media['repeat'] = 100

    def _count_thread(self, aob, index):
        aob_str: str = aob['aob_string']
        self.searcher.set_search_size('array')
        self.searcher.search_memory_value(aob_str)
        self.count_queue.put((index, len(self.searcher.results)))


    def process_selected_file(self, resp: Response, ab_file: AOBFile):
        if not ab_file.is_final() and not ab_file.is_initial():
            self.flow = self.FLOW_RESULTS
            resp.media['is_initial_search'] = ab_file.count_aob_results() == 0
            resp.media['number_of_results'] = ab_file.count_aob_results()
            resp.media['is_final'] = ab_file.is_final()
            addr = self.base_converter.convert(self.mem(), str(self.current_address))
            if self.current_search_type == 'address' and (not addr or addr <= 0xFFFF):
                self.current_address = "0"
            resp.media['value'] = self.current_value if self.current_search_type == 'value' else self.current_address
            resp.media['type'] = self.current_search_type
            resp.media['size'] = self.current_value_size
            resp.media['valid_types'] = ['address']
            if ab_file.count_aob_results() > 0:
                resp.media['valid_types'].append('value')
            resp.media['results'] = ab_file.get_results()
        if ab_file.is_initial():
            if ab_file.has_memory_file():
                self.flow = self.FLOW_INITIAL_COMPLETE
            else:
                self.flow = self.FLOW_START
                resp.media['range'] = ab_file.get_range()
        elif ab_file.count_aob_results() == 0:
            self.flow = self.FLOW_NO_RESULTS
            resp.media['range'] = ab_file.get_range()

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

        def __init__(self, _memory, _name, _type=None, _address_value=None, _range=None, _size=None):
            super().__init__(target=self.process)
            self.memory: Process = _memory
            self.base_converter = BaseConvert()
            self.current_name = _name
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
            if not AOB.directory.exists():
                os.makedirs(AOB.directory, exist_ok=True)

            self.aob_file: AOBFile = AOBFile(directory=AOB.directory, filename=self.current_name+'.aob')
            self.progress = Progress()
            self.error = ""
            self.operation_control = DataStore().get_operation_control()


        def get_file(self):
            return self.aob_file

        def get_progress(self):
            return self.progress.get_progress()

        def is_initial_needed(self):
            if not self.aob_file.exists():
                return True
            else:
                if not self.aob_file.is_final() and self.aob_file.count_aob_results() == 0 and not self.aob_file.get_memory_file().exists():
                    return True
                return False

        def process_address_run(self):
            if self.is_initial_needed():
                # start needs to be an address
                self.progress.add_constraint(0, 100, 1.0)
                au = AOBUtilities(self.memory, DataStore().get_operation_control(), self.progress)
                start, end, self.current_range = au.calculate_range(self.current_address, self.current_range)
                if start == -1:  # error with range
                    self.error = "Invalid address for this process."
                    return
                self.progress.increment(30)
                try:
                    data = self.memory.read_memory(start, (ctypes.c_byte * (end - start))())
                except OSError:
                    self.error = "Invalid region to scan."
                    return
                self.progress.increment(40)
                self.aob_file.set_process(DataStore().get_process('aob'))
                self.aob_file.set_name(self.current_name)
                self.aob_file.set_range(self.current_range)
                self.aob_file.set_offset(self.current_address-start)
                self.aob_file.set_length(end-start)
                self.aob_file.set_initial(True)
                self.aob_file.write()
                with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)), 'wb') as d_file:
                    d_file.write(data)
                self.progress.mark()
            else: #we have an aob file
                self.aob_file.set_initial(False)
                number_of_results = self.aob_address_search()
                if number_of_results >= 0:
                    if number_of_results == 0:
                        self.aob_file.set_final()
                    self.aob_file.write()

        def process_value_run(self):
            if not self.aob_file.exists():
                logging.error("Trying to do a value search without an .aob file!")
                return
            try:
                number_of_results = self.aob_value_search()
            except AOBException as e:
                self.error = 'Search Failed: {}'.format(e.get_message())
                return
            if number_of_results >= 0:
                if number_of_results == 0:
                    self.aob_file.set_final()
                self.aob_file.write()


        def process(self):
            self.aob_file.remove_dupes()
            try:
                if not self.is_value:
                    self.process_address_run()
                else:
                    self.process_value_run()
            except BreakException:
                pass


        def aob_value_search(self):
            au = AOBUtilities(self.memory, self.operation_control, self.progress)
            walker = AOBWalk(aob_file=self.aob_file, max_size=50, filter_result_size=6)
            if self.current_value:
                sz_map = {'byte_1': AOBWalk.BYTE, 'byte_2': AOBWalk.BYTE_2, 'byte_4': AOBWalk.BYTE_4, 'byte_8': AOBWalk.BYTE_8}
                walker.set_result_value_filter(self.current_value, sz_map[self.current_size], self.memory)
            self.progress.add_constraint(0, au.get_total_memory_size()[0], 1.0)
            walker.search(self.memory, progress=self.progress)
            self.progress.mark()
            return self.aob_file.count_aob_results()

        def aob_address_search_memory(self, new_data) -> int:
            with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)), 'rb') as d_file:
                old_data = d_file.read()
                old_data = (ctypes.c_byte * len(old_data))(*old_data)
            with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)), 'wb') as d_file:
                d_file.write(new_data)
            return self.compare_data(new_data, old_data)

        def aob_address_search_aob(self, new_data):
            with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)), 'wb') as d_file:
                d_file.write(new_data)
            return self.compare_aob(new_data)

        def aob_address_search(self):
            self.progress.add_constraint(0, 1, 0.1)
            start = self.current_address - self.aob_file.get_offset()
            end = start+self.aob_file.get_length()
            try:
                new_data = self.memory.read_memory(start, (ctypes.c_byte * (end - start))())
            except OSError:
                self.progress.mark()
                return 0
            self.progress.mark()
            if self.aob_file.count_aob_results() == 0:
                number_of_results = self.aob_address_search_memory(new_data)
            else:
                number_of_results = self.aob_address_search_aob(new_data)
            return number_of_results

        def compare_aob(self, new_data):
            aob_list = self.aob_file.get_aob_list()
            self.progress.add_constraint(0, len(aob_list), 0.90)
            for i in range(len(aob_list)-1, -1, -1):
                self.operation_control.test()
                aob = aob_list[i]
                self.progress.increment(1)
                new_aob = []
                index = aob['offset'] + self.aob_file.get_offset()
                for bt in aob['aob_array']:
                    if bt == '??':
                        new_aob.append('??')
                    else:
                        new_byte = value_to_hex(new_data[index], aob=True)
                        new_aob.append('??' if new_byte != bt else bt)
                    index += 1
                if all(x == '??' or x == '00' for x in new_aob):
                    self.aob_file.remove_index(i)
                elif round(new_aob.count('??') / len(new_aob), 1) > 0.4:
                    self.aob_file.remove_index(i)
                else:
                    self.aob_file.modify_index_array(i, new_aob)
            self.aob_file.remove_dupes()
            self.progress.mark()
            return self.aob_file.count_aob_results()

        def compare_data(self, new_data, old_data) -> int:
            data_length = len(new_data)
            self.progress.add_constraint(0, data_length, 0.9)
            current_string = []
            start_run = -1
            for i in range(0, data_length):
                self.progress.increment(1)
                self.operation_control.test()
                if start_run == -1:
                    if new_data[i] == old_data[i] and not self.are_zeros(new_data, old_data, i, data_length): #if we have a match and they aren't x bytes of zeros
                        start_run = i
                        current_string = [value_to_hex(new_data[i], aob=True)]
                else:
                    if new_data[i] == old_data[i] and not self.are_zeros(new_data, old_data, i, data_length):  # if we have a match and they aren't x bytes of zeros
                        current_string.append(value_to_hex(new_data[i], aob=True))
                    elif new_data[i] != old_data[i] and not self.are_diffs(new_data, old_data, i, data_length): #if we don't have a match, but we also don't have x bytes of mismatches
                        current_string.append('??')
                    else: #we have 5 or more mismatches coming up.  end the run
                        if len(current_string) >= self.smallest_run and not all(elem == '00' or elem == '??' for elem in current_string):
                            self.aob_file.add_aob_array(current_string, start_run)
                        current_string = []
                        start_run = -1
            self.progress.mark()
            return self.aob_file.count_aob_results()

        def stop_run(self, start_run, current_run, aob_table, offset, new_data):
            if current_run >= self.smallest_run:
                b_data = (ctypes.c_byte * current_run)(*new_data[start_run:start_run + current_run])
                aob_table.append(
                    {'offset': start_run + offset, 'size': current_run, 'aob': bytes_to_aobstr(b_data)})
            current_run = 0
            return current_run

        def do_run(self, start_run, current_run, i, aob_table, offset, new_data):
            if current_run == 0:
                start_run = i
            current_run += 1
            if current_run == self.largest_run:
                b_data = (ctypes.c_byte * current_run)(*new_data[start_run:start_run + current_run])
                aob_table.append(
                    {'offset': start_run + offset, 'size': current_run, 'aob': bytes_to_aobstr(b_data)})
                current_run = 0
            return current_run, start_run

        def are_zeros(self, new_data, old_data, i, data_length):
            if i+self.consecutive_zeros >= data_length:
                return False
            if new_data[i: i+self.consecutive_zeros] == old_data[i: i+self.consecutive_zeros]:
                return new_data[i: i+self.consecutive_zeros] == [0]*self.consecutive_zeros or new_data[i: i+self.consecutive_zeros] == [-1]*self.consecutive_zeros
            return False

        def are_diffs(self, new_data, old_data, i, data_length):
            count = 0
            if i+self.consecutive_zeros >= data_length:
                return False
            for j in range(i, i+self.consecutive_zeros):
                if new_data[j] != old_data[j]:
                    count += 1
            return count == self.consecutive_zeros

        def write(self, aobs):
            with open(self.aob_match_file, 'wt') as i_file:
                i_file.write("Process: {}\nName: {}\nValid: {}\nSearched: true\n\n".format(self.current_process, self.current_name, len(aobs)))
                for aob in aobs:
                    i_file.write("Size: {:<5} Offset: {:<15X} {}\n".format(aob[0], aob[1], aob[2]))


