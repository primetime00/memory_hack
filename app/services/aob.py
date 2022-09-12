import ctypes
import logging
import os
from io import StringIO
from pathlib import Path
from threading import Thread

from falcon import Request, Response, MEDIA_JSON

from app.helpers import DynamicHTML, MemoryHandler, DataStore
from app.helpers import memory_utils, AOBWalk, AOBFile, Progress
from app.helpers.exceptions import AOBException, BreakException


class AOB(MemoryHandler):
    directory = Path('.aob')

    def __init__(self):
        super().__init__()
        self.handle_map = {
            "AOB_INITIALIZE": self.handle_initialization,
            "AOB_SELECT": self.handle_select,
            "AOB_RESET": self.handle_reset,
            "AOB_SEARCH": self.handle_search,
            "AOB_DOWNLOAD": self.handle_download,
            "AOB_UPLOAD": self.handle_upload,
            "AOB_STATUS": self.handle_initialization
        }
        self.aob_work_thread: AOB.AOBWorkThread = None
        self.current_name = ''
        self.set_current_name('')
        self.current_search_type = 'address'
        self.current_address = 0
        self.current_range = 0
        self.round = 0
        self.current_value = None
        self.current_value_size = None

        self.reset()
        self.delete_memory()

    def release(self):
        self.reset()

    def reset(self):
        if self.aob_work_thread and self.aob_work_thread.is_alive():
            self.memory.break_search()
            self.aob_work_thread.join()
        self.set_current_name('')
        self.current_search_type = 'address'
        self.current_address = 0
        self.current_range = 0
        self.round = 0
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

    def is_running(self):
        return self.aob_work_thread is not None and self.aob_work_thread.is_alive()

    def is_ready_for_start(self):
        if self.aob_work_thread and self.aob_work_thread.is_alive():
            return False
        if self.current_name == "":
            return True
        return False
    def is_searching(self):
        return self.aob_work_thread and self.aob_work_thread.is_alive()

    def get_search_progress(self):
        if not self.is_searching():
            return 0
        return self.aob_work_thread.get_progress()

    def has_searched(self):
        return not self.is_ready_for_start() and not self.is_searching()

    def handle_reset(self, req: Request, resp: Response):
        process = req.media['process']
        self.reset()
        resp.media['state'] = "AOB_STATE_START"

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
        except AOBException as e:
            resp.media['error'] = 'Upload failed: {}'.format(e.get_message())
            return
        aob_file.write()
        resp.media['message'] = 'Upload complete'
        resp.media['names'] = self.get_aob_list()


    def handle_search(self, req: Request, resp: Response):
        name = req.media["name"]
        search_type = req.media["search_type"]
        search_range = req.media["range"]
        address_value = req.media["address_value"]
        value_size = req.media["value_size"]
        self.set_current_name(name)
        try:
            self.aob_work_thread = AOB.AOBWorkThread(self.memory, name, search_type, address_value, search_range, value_size)
        except ValueError as e:
            resp.media['error'] = 'Could not start: {}'.format(e)
            return
        self.aob_work_thread.start()
        resp.media['state'] = 'AOB_STATE_SEARCHING'
        resp.media['repeat'] = 1000
        resp.media['progress'] = self.get_search_progress()

    def handle_initialization(self, req: Request, resp: Response):
        #We just loaded the page. Check if search is idle, running, or finished
        if self.is_ready_for_start():
            resp.media['state'] = 'AOB_STATE_START'
            resp.media['repeat'] = 0
            resp.media['search_type'] = "address"
            resp.media['valid_searches'] = ['address']
            if self.current_name in self.get_aob_list():
                resp.media['valid_searches'].append('value')
            resp.media['names'] = self.get_aob_list()
        elif self.is_searching():
            resp.media['state'] = 'AOB_STATE_SEARCHING'
            resp.media['repeat'] = 1000
            resp.media['progress'] = self.get_search_progress()
        elif self.has_searched():
            if not self.aob_work_thread: #we refreshed the page?
                req.media['name'] = self.current_name
                self.handle_select(req, resp)
                resp.media['names'] = self.get_aob_list()
                resp.media['name'] = self.current_name
                resp.media['select'] = self.current_name if self.current_name in self.get_aob_list()  else '_null'
            elif self.aob_work_thread.is_errored():
                resp.media['state'] = 'AOB_STATE_START' if len(self.aob_work_thread.get_results()) == 0 else 'AOB_STATE_CONTINUE'
                resp.media['error'] = self.aob_work_thread.get_error()
                resp.media['number_of_results'] = len(self.aob_work_thread.get_results())
                resp.media['search_results'] = self.aob_work_thread.get_results()
            else:
                resp.media['state'] = 'AOB_STATE_CONTINUE'
                resp.media['search_type'] = self.current_search_type
                resp.media['number_of_results'] = len(self.aob_work_thread.get_results())
                resp.media['search_results'] = self.aob_work_thread.get_results()
                resp.media['initial_search'] = self.aob_work_thread.is_initial_search()
                resp.media['is_final'] = self.aob_work_thread.is_final_search()
                resp.media['names'] = self.get_aob_list()
            resp.media['last_search'] = ''
            resp.media['search_round'] = self.round
            resp.media['repeat'] = 0

    def handle_select(self, req: Request, resp: Response):
        name = req.media['name']
        self.set_current_name(name)
        resp.media['valid_searches'] = ['address']
        if self.current_name in self.get_aob_list():
            ab_file = AOBFile(directory=AOB.directory, filename=self.current_name+'.aob')
            resp.media['state'] = 'AOB_STATE_CONTINUE'
            resp.media['search_results'] = ab_file.get_results()
            resp.media['is_initial_search'] = ab_file.count_aob_results() == 0
            resp.media['number_of_results'] = ab_file.count_aob_results()
            resp.media['is_final'] = ab_file.is_final()
            if ab_file.count_aob_results() > 0:
                resp.media['valid_searches'].append('value')

    def process(self, req: Request, resp: Response):
        resp.media = {}
        command = req.media['command']
        assert (command in self.handle_map)
        resp.content_type = MEDIA_JSON
        try:
            self.handle_map[command](req, resp)
        except AOBException as e:
            resp.media['error'] = e.get_message()

    def get_aob_list(self):
        return [x.stem for x in AOB.directory.glob('*.aob')]

    class AOBWorkThread(Thread):
        smallest_run = 5
        consecutive_zeros = 5
        INITIAL_SEARCH_COMPLETE = "AOB_INITIAL_SEARCH_COMPLETE"
        SEARCH_COMPLETE = "AOB_SEARCH_COMPLETE"
        ERROR = "AOB_ERROR"

        def __init__(self, _memory, _name, _type=None, _address_value=None, _range=None, _size=None):
            super().__init__(target=self.process)
            self.memory = _memory
            self.current_name = _name
            self.current_address = int(_address_value, 16) if _type == 'address' else 0
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
                os.mkdir(AOB.directory)

            self.aob_file: AOBFile = AOBFile(directory=AOB.directory, filename=self.current_name+'.aob')
            self.current_aobs = []
            self.progress = Progress()
            self.status = {}
            self.operation_control = DataStore().get_operation_control()

        def get_progress(self):
            return self.progress.get_progress()

        def is_errored(self):
            return self.status['status'] == self.ERROR

        def is_initial_search(self):
            return self.status['status'] == self.INITIAL_SEARCH_COMPLETE

        def is_final_search(self):
            if "final" in self.status:
                return self.status["final"]
            return False

        def is_continued_search(self):
            return self.status['status'] == self.SEARCH_COMPLETE

        def get_error(self):
            return self.status['error']

        def get_results(self):
            if 'results' in self.status:
                return self.status['results']
            return []

        def calculate_range(self, proc):
            start, end = self.memory.find_heap_data(proc, self.current_address)
            if start == -1:
                return start, end
            want_start = self.current_address - int((self.current_range / 2))
            if want_start > start:
                start = want_start
            want_end = self.current_address + int((self.current_range / 2))
            if want_end < end:
                end = want_end
            actual_range = end - start
            self.current_range = actual_range
            return start, end

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
                start, end = self.calculate_range(self.memory.handle)
                if start == -1:  # error with range
                    self.status = {'status': self.ERROR, 'error': "Invalid address for this process."}
                    return
                self.progress.add_constraint(0, 1, 1)
                self.progress.increment(0.3)
                data = self.memory.read(start, (ctypes.c_byte * (end - start))())
                self.progress.increment(0.8)
                self.aob_file.set_process(DataStore().get_process())
                self.aob_file.set_name(self.current_name)
                self.aob_file.set_range(self.current_range)
                self.aob_file.set_offset(self.current_address-start)
                self.aob_file.set_length(end-start)
                self.aob_file.write()
                with open(AOB.directory.joinpath('{}.mem'.format(self.current_name)), 'wb') as d_file:
                    d_file.write(data)
                self.progress.mark()
                self.status = {'status': self.INITIAL_SEARCH_COMPLETE, 'results': []}
            else: #we have an aob file
                number_of_results = self.aob_address_search()
                results = []
                if number_of_results >= 0:
                    results = self.aob_file.get_results()
                    if number_of_results == 0:
                        self.aob_file.set_final()
                    self.aob_file.write()
                self.status = {'status': self.SEARCH_COMPLETE, 'results': results, 'final': self.aob_file.is_final()}

        def process_value_run(self):
            if not self.aob_file.exists():
                logging.error("Trying to do a value search without an .aob file!")
                return
            try:
                number_of_results = self.aob_value_search()
            except AOBException as e:
                self.status = {'status': self.ERROR, 'error': 'Search Failed: {}'.format(e.get_message())}
                self.status['results'] = self.aob_file.get_results()
                return
            results = []
            if number_of_results >= 0:
                results = self.aob_file.get_results()
                if number_of_results == 0:
                    self.aob_file.set_final()
                self.aob_file.write()
            self.status = {'status': self.SEARCH_COMPLETE, 'results': results, 'final': self.aob_file.is_final()}


        def process(self):
            self.progress = Progress()
            try:
                if not self.is_value:
                    self.process_address_run()
                else:
                    self.process_value_run()
            except BreakException as br:
                self.status = {'status': self.SEARCH_COMPLETE, 'results': self.aob_file.get_results(), 'final': self.aob_file.is_final()}


        def aob_value_search(self):
            def progress_func(current, total):
                if current == 0:
                    self.progress.add_constraint(0, total, 1)
                self.progress.increment(current)

            walker = AOBWalk(aob_file=self.aob_file, max_size=50, filter_result_size=1)
            if self.current_value:
                sz_map = {'byte': AOBWalk.BYTE, '2byte': AOBWalk.BYTE_2, '4byte': AOBWalk.BYTE_4}
                walker.set_result_value_filter(self.current_value, sz_map[self.current_size], self.memory)

            walker.search(self.memory, progress=progress_func)
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
            new_data = self.memory.read(start, (ctypes.c_byte * (end - start))())
            self.progress.mark()
            if self.aob_file.count_aob_results() == 0:
                number_of_results = self.aob_address_search_memory(new_data)
            else:
                number_of_results = self.aob_address_search_aob(new_data)
            return number_of_results

        def compare_aob(self, new_data):
            aob_list = self.aob_file.get_aob_list()
            self.progress.add_constraint(0, len(aob_list), 0.35)
            j = 0
            for i in range(len(aob_list)-1, -1, -1):
                if self.operation_control.is_control_break():
                    raise BreakException()
                aob = aob_list[i]
                self.progress.increment(j)
                j += 1
                new_aob = []
                index = aob['offset'] + self.aob_file.get_offset()
                for bt in aob['aob_array']:
                    if bt == '??':
                        new_aob.append('??')
                    else:
                        new_byte = memory_utils.value_to_hex(new_data[index], aob=True)
                        new_aob.append('??' if new_byte != bt else bt)
                    index += 1
                if all(x == '??' or x == '00' for x in new_aob):
                    self.aob_file.remove_index(i)
                else:
                    self.aob_file.modify_index_array(i, new_aob)
            self.progress.mark()
            def progress_func(current, total):
                if current == 0:
                    self.progress.add_constraint(0, total, 0.55)
                self.progress.increment(current)

            ##search our AOBs to see if they produce only 1 result.  This may take a little while
            walker = AOBWalk(aob_file=self.aob_file, max_size=50, filter_result_size=1)
            walker.search(self.memory, progress=progress_func)
            self.progress.mark()
            return self.aob_file.count_aob_results()

        def compare_data(self, new_data, old_data) -> int:
            data_length = len(new_data)
            self.progress.add_constraint(0, data_length, 0.9)
            aob_table = []
            current_string = []
            start_run = -1
            for i in range(0, data_length):
                self.progress.increment(i)
                if self.operation_control.is_control_break():
                    raise BreakException()
                if start_run == -1:
                    if new_data[i] == old_data[i] and not self.are_zeros(new_data, old_data, i, data_length): #if we have a match and they aren't x bytes of zeros
                        start_run = i
                        current_string = [memory_utils.value_to_hex(new_data[i], aob=True)]
                else:
                    if new_data[i] == old_data[i] and not self.are_zeros(new_data, old_data, i, data_length):  # if we have a match and they aren't x bytes of zeros
                        current_string.append(memory_utils.value_to_hex(new_data[i], aob=True))
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
                    {'offset': start_run + offset, 'size': current_run, 'aob': memory_utils.bytes_to_aobstr(b_data)})
            current_run = 0
            return current_run

        def do_run(self, start_run, current_run, i, aob_table, offset, new_data):
            if current_run == 0:
                start_run = i
            current_run += 1
            if current_run == self.largest_run:
                b_data = (ctypes.c_byte * current_run)(*new_data[start_run:start_run + current_run])
                aob_table.append(
                    {'offset': start_run + offset, 'size': current_run, 'aob': memory_utils.bytes_to_aobstr(b_data)})
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


