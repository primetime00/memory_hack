from app.helpers.exceptions import AOBException, BreakException
from mem_edit import Process
from app.helpers.data_store import DataStore
from app.helpers.aob_file import AOBFile
from app.helpers.memory_utils import value_to_bytes
import ctypes

class AOBWalk:
    BYTE = 1
    BYTE_2 = 2
    BYTE_4 = 4
    ARRAY = 8
    NONE = 0
    def __init__(self, aob_file: AOBFile = None, max_size=35, filter_result_size=-1, filter_result_value=(NONE, 0, None)):
        self.aob_file = aob_file
        self.max_size = max_size

        self.aob_tree = {}
        self.bad_aob = []
        self.normal_aob = []
        self.good_aob = []
        self.aob_map = {}
        self.filter_result_size = filter_result_size
        self.filter_result_value = self._set_value(filter_result_value)
        self.operation_control = DataStore().get_operation_control()


    def add_aob_string(self, aob_string:str, black_list=('00', '??')):
        aob_array = aob_string.split(" ")
        aob_item = AOBFile.create_aob(len(aob_array), 0, aob_string)
        self.aob_map[aob_item['aob_string']] = {'addresses': [], 'offset': aob_item['offset']}
        aob = aob_array
        best_pos = -1

        for i in range(0, len(aob)):
            if aob[i] not in black_list:
                best_pos = i
                break

        for i in range(0, len(aob)):
            if aob[i] not in ('00', '??', 'FF', '01'):
                best_pos = i

        if best_pos == -1:
            raise AOBException("Could not add aob {} to walker".format(aob))
        else:
            if aob[best_pos] not in self.aob_tree:
                self.aob_tree[aob[best_pos]] = []
            element = {'start': best_pos, 'aob_data': aob_item, 'addresses': []}
            self.aob_tree[aob[best_pos]].append(element)

    def add_normal_aob(self, aob_item, black_list=('00', '??')):
        found = False
        aob = aob_item['aob_array']
        for i in range(0, len(aob)):
            if aob[i] not in black_list:
                found = True
                if aob[i] not in self.aob_tree:
                    self.aob_tree[aob[i]] = []
                element = {'start': i, 'aob_data': aob_item, 'addresses': []}
                self.aob_tree[aob[i]].append(element)
                break
        if not found:
            raise AOBException("Could not add aob {} to walker".format(aob))

    def parse_aob(self, el):
        aob = el['aob_array']
        if all(x == '00' or x == '??' for x in aob):
            self.bad_aob.append(el)
            return
        self.aob_map[el['aob_string']] = {'addresses': [], 'offset': el['offset']}
        if all(x == '00' or x == '??' or x == '01' or x == 'FF' for x in aob):
            self.normal_aob.append(el)
            return
        self.good_aob.append(el)

    def get_addresses(self, aob):
        if aob not in self.aob_map:
            raise AOBException('Could not find AOB result for {}'.format(aob))
        return self.aob_map[aob]['addresses']

    def get_aob_map(self):
        return self.aob_map

    def create(self):
        if self.aob_file:
            self.aob_tree = {}
            aob_list = self.aob_file.get_aob_list()
        else:
            return

        for item in aob_list:
            if len(item['aob_array']) > self.max_size:
                continue
            self.parse_aob(item)
        for item in self.good_aob:
            self.add_normal_aob(item, black_list=('00', '??', '01', 'FF'))
        for item in self.normal_aob:
            self.add_normal_aob(item)
        if len(self.aob_tree) == 0:
            raise AOBException('No AOBs could be created.')

    def search(self, memory: Process, progress=None):
        self.create()
        if len(self.aob_tree) == 0:
            raise AOBException('No AOBs to be searched')
        index = 0
        for start, end in memory.list_mapped_regions():
            try:
                size = end-start
                region_buffer = (ctypes.c_byte * size)()
                memory.read_memory(start, region_buffer)
                data = bytes(region_buffer)
                keys = [int(x,16) for x in list(self.aob_tree.keys())]
                pos = 0
                #for k in keys:
                #    while pos >= 0 and pos < size:
                #        if self.operation_control.is_control_break():
                #            raise BreakException()
                #        pos = data.find(k, pos)
                #        if pos > -1:
                #            self.process_match(data, pos, data[pos], start)
                #            pos += 1
                #data.find(keys[0])
                for i in range(0, len(data)):
                    if self.operation_control.is_control_break():
                        raise BreakException()
                    if data[i] in keys:
                        self.process_match(data, i, data[i], start)
                    if progress:
                        progress.increment(1)
            except OSError:
                if progress:
                    progress.increment(end-start)
            finally:
                index += 1
        self.filter()

    def filter(self):
        self.remove_zero_matches()
        if self.filter_result_size > 0:
            self.remove_multiple_matches(self.filter_result_size)
        if self.filter_result_value[0] != AOBWalk.NONE:
            self.filter_value()


    def process_match(self, data, offset, key, global_offset):
        bucket = self.aob_tree['{0:0{1}X}'.format((key + (1 << 8)) % (1 << 8), 2)]
        for b in bucket:
            start = b['start']
            aob_data = b['aob_data']
            length = len(aob_data['aob_bytes'])
            match = True
            if offset - start < 0 or (offset - start)+length >= len(data):
                continue
            for i in range(0, length):
                if aob_data['aob_bytes'][i] > 255:
                    continue
                if data[offset-start+i] != aob_data['aob_bytes'][i]: #not a match
                    match = False
                    break
            if match:
                b['addresses'].append(global_offset+offset-start)
                self.aob_map[aob_data['aob_string']]['addresses'].append(global_offset+offset-start)

    def remove_multiple_matches(self, size):
        if not self.aob_map:
            return
        mults = [aob for aob, data in self.get_aob_map().items() if len(data['addresses']) > size]
        for m in mults:
            if self.aob_file:
                self.aob_file.remove_aob_string(m)
            del self.aob_map[m]
        if self.aob_file:
            for b in self.bad_aob:
                self.aob_file.remove_aob_string(" ".join(b))

    def remove_zero_matches(self):
        if not self.aob_map:
            return
        zeros = [aob for aob, data in self.get_aob_map().items() if len(data['addresses']) == 0]
        for m in zeros:
            if self.aob_file:
                self.aob_file.remove_aob_string(m)
            del self.aob_map[m]
        if self.aob_file:
            for b in self.bad_aob:
                self.aob_file.remove_aob_string(" ".join(b))


    def filter_value(self):
        val = self.filter_result_value[1]
        mem = self.filter_result_value[2]
        dc =  self.aob_map.copy()
        for aob, data in dc.items():
            if self.operation_control.is_control_break():
                raise BreakException()
            offset = data['offset']
            addr = data['addresses'][0]
            read_address = addr-offset
            try:
                read = mem.read_memory(read_address, (ctypes.c_byte * len(val))())
            except Exception as e:
                if self.aob_file:
                    self.aob_file.remove_aob_string(aob)
                del self.aob_map[aob]
                continue
            if read[0:] != val[0:]:
                if self.aob_file:
                    self.aob_file.remove_aob_string(aob)
                del self.aob_map[aob]

    def set_result_value_filter(self, value, size, memory):
        self.filter_result_value = self._set_value((size, value, memory))

    def _set_value(self, filter_result_value):
        tp, val, mem = filter_result_value
        if tp == AOBWalk.NONE:
            return filter_result_value
        try:
            if tp == AOBWalk.BYTE:
                val = value_to_bytes(val, 1)
            elif tp == AOBWalk.BYTE_2:
                val = value_to_bytes(val, 2)
            elif tp == AOBWalk.BYTE_4:
                val = value_to_bytes(val, 4)
            else: #better be a hex string
                val = value_to_bytes(val, 0)
        except Exception as e:
            raise AOBException('Could not parse value {}'.format(filter_result_value))
        return filter_result_value[0], val, mem


