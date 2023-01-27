import logging
import pickle
import re
from io import BytesIO
from pathlib import Path

from app.helpers.directory_utils import aob_directory
from app.helpers.exceptions import AOBException


class AOBFile():
    _pattern = re.compile('^Size: (\d+)\s*Offset: (-?[0-9A-F]+)\s*([0-9A-F ?]+)$')
    smallest_run = 5
    consecutive_wildcards = 5
    header = ['Process: ', 'Name: ', 'Range: ', 'Offset: ', 'Length: ', 'Valid: ']
    FILE_STATE_NOT_EXIST = 0
    FILE_STATE_INITIAL_RESULTS = 1
    FILE_STATE_HAS_RESULTS = 2
    FILE_STATE_NO_RESULTS = 3
    FILE_STATE_NEEDS_SEARCH = 4
    _FILE_VERSION = 1

    def __init__(self, directory: Path = aob_directory, filename=None):
        self.process = ""
        self.directory = directory
        self.name = ""
        self.range = 0
        self.address_offset = 0
        self.length = 0
        self.valid = 0
        self.final = False
        self.initial = True
        self.data_list = []
        self.aob_list = []
        self.file_state = AOBFile.FILE_STATE_NOT_EXIST
        self.filename = filename
        self._version = AOBFile._FILE_VERSION
        if self.filename and self.directory.joinpath(self.filename).exists():
            self.read()

    def read(self, filename=None):
        if filename:
            self.filename = filename
        else:
            filename = self.filename
        if not filename:
            raise AOBException('No filename given.')
        path = self.directory.joinpath(filename)
        if not path.exists():
            raise AOBException("Cannot find aob file {}".format(str(path.absolute())))
        with open(path, "rb") as f:
            self.read_stream(f)

    def read_stream(self, handle):
        try:
            data = pickle.load(handle)
            self.process = data['process']
            self.range = data['range']
            self.address_offset = data['offset']
            self.length = data['length']
            self.valid = data['valid']
            self.final = data['final']
            self.initial = data['initial']
            self.data_list = data['aob_data']
            self._version = data.get('_version', 1)
        except Exception as e:
            raise AOBException('Could not parse AOB data')
        self.valid = True
        self.validate()
        if len(self.data_list) == 0:
            self.file_state = AOBFile.FILE_STATE_NEEDS_SEARCH
        elif len(self.data_list) == 1:
            self.file_state = AOBFile.FILE_STATE_INITIAL_RESULTS
        elif len(self.data_list) >= 2:
            if len(self.data_list[-1]) > 0:
                self.file_state = AOBFile.FILE_STATE_HAS_RESULTS
            else:
                self.file_state = AOBFile.FILE_STATE_NO_RESULTS


    def get_state(self):
        return self.file_state

    def validate(self):
        if not self.name:
            raise AOBException('Could not find name in AOB file.')
        if self.range < 2:
            raise AOBException('Invalid range in AOB file.')
        if self.length < 2:
            raise AOBException('Invalid length in AOB file.')
        if not self.filename:
            raise AOBException('AOB file needs a filename.')


    @staticmethod
    def create_aob(size: int, offset:int, aob:str):
        res = {'size': size, 'offset': offset, 'aob_string': aob, 'aob_array': aob.split(" ")}
        res['aob_bytes'] = [int(x, 16) if x != '??' else 256 for x in res['aob_array']]
        return res

    def create_aob_from_array(self, mem_start: int, aob_values: list):
        offset = self.address_offset - mem_start
        size = len(aob_values)
        aob_string = ""
        for item in aob_values:
            if item <= 255:
                aob_string += '{:02X} '.format(item)
            else:
                aob_string += '?? '

        results = []
        aob_array, start, length = self.strip(aob_array)
        mem_start = mem_start + start
        groups = self.divide(aob_array, wildcard_length=self.consecutive_wildcards)
        if len(groups)>1:
            pass
        for item in groups:
            na_start = mem_start + item['start']
            if len(item['aob']) < self.smallest_run:
                continue
            res = {'size': len(item['aob']), 'offset': na_start, 'aob_string': ' '.join(item['aob']), 'aob_array': item['aob']}
            res['aob_bytes'] = [int(x, 16) if x != '??' else 256 for x in res['aob_array']]
            results.append(res)
        return results


    def add_aob_array(self, aob_array, run_start):
        aobs = self.create_aob_from_array(run_start - self.address_offset, aob_array)
        if aobs:
            self.aob_list.extend(aobs)
        else:
            logging.warning("Could not add AOBs.  There were none to add [{}]".format(" ".join(aob_array)))
        self.valid = len(self.aob_list)


    def modify_index_array(self, index, new_aob):
        aob_item = self.aob_list[index]
        offset = aob_item['offset']
        aobs = self.create_aob_from_array(offset, new_aob)
        self.aob_list.pop(index)
        for i in range(len(aobs)-1, -1, -1):
            aob = aobs[i]
            if all(x == '??' or x == '00' for x in aob['aob_array']):
                aobs.pop(i)
        if aobs:
            self.aob_list.extend(aobs)
        else:
            logging.warning("Could not modify AOB.  There were none to add.\noriginal[{}]\nnew[{}]".format(" ".join(aob_item['aob_array']), " ".join(new_aob)))


    def write(self):
        self.validate()
        path = self.directory.joinpath('{}'.format(self.filename))
        data = {
            'process': self.process,
            'name': self.name,
            'range': self.range,
            'offset': self.address_offset,
            'length': self.length,
            'valid': self.valid,
            'final': self.final,
            'initial': self.initial,
            'aob_data': self.data_list,
            '_version': AOBFile._FILE_VERSION
        }
        try:
            with open(path.absolute(), "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            raise AOBException('Could not write AOB file {} [{}]'.format(str(path.absolute()), e))

    def get_filename(self) -> str:
        if self.name:
            return self.name+'aob'
        if self.filename:
            return self.filename
        raise AOBException('No filename given.')

    def get_stream(self, filename=None) -> BytesIO:
        if filename:
            path = self.directory.joinpath(filename)
        else:
            path = self.directory.joinpath(self.filename)
        if not path.exists():
            raise AOBException('Cannot find AOB file to stream {}'.format(str(path.absolute())))
        with open(path, 'rb') as f:
            data = f.read()
            return BytesIO(data)

    def get_results(self):
        self.validate()
        results = []
        if self.data_list and len(self.data_list) > 1:
            for item in sorted(self.data_list[-1], key=lambda x: x['offset_from_address']):
                res = {'size': item['size'], 'offset': '{:X}'.format(item['offset_from_address']),
                       'aob': item['aob_string'] }
                       #'aob': item['aob_string'] if item['size'] <= 50 else " ".join(item['aob_array'][0:50])}
                results.append(res)
        return results

    def is_final(self):
        return self.final

    def set_final(self):
        self.final = True

    def is_initial(self):
        return self.initial

    def set_initial(self, ini):
        self.initial = ini

    def get_aob_list(self):
        return self.aob_list

    def count_aob_results(self):
        if self.data_list and len(self.data_list) > 1:
            return len(self.data_list[-1])
        return 0

    def exists(self):
        if not self.filename:
            raise AOBException('AOB file does not have a filename.')
        return self.directory.joinpath(self.filename).exists()

    def set_process(self, _process: str):
        self.process = _process

    def set_name(self, _name: str):
        if _name != self.name: #we loaded a new file or something
            self.name = _name
            self.filename = self.name+'.aob'
            if not self.directory.joinpath(self.filename).exists():
                self.file_state = AOBFile.FILE_STATE_NOT_EXIST
            else:
                self.read()




    def set_range(self, _range: int):
        self.range = _range

    def set_address_offset(self, _offset: int):
        self.address_offset = _offset

    def set_length(self, _length: int):
        self.length = _length

    def get_address_offset(self) -> int:
        return self.address_offset

    def get_length(self) -> int:
        return self.length

    def get_range(self) -> int:
        return self.range

    def remove_index(self, index=0):
        if self.data_list and len(self.data_list) > 1:
            self.data_list[-1].pop(index)

    def remove_aob_string(self, aob_string):
        aob_string_list = [x['aob_string'] for x in self.aob_list]
        try:
            pos = aob_string_list.index(aob_string)
            self.remove_index(pos)
        except ValueError:
            pass

    def get_memory_file(self):
        path = self.directory.joinpath('{}.mem'.format(Path(self.filename).stem))
        return path

    def remove_dupes(self):
        dupe = {}
        for i in range(len(self.aob_list)-1, -1, -1):
            aob = self.aob_list[i]
            if len(aob['aob_string']) > 100:
                continue
            if aob['aob_string'] not in dupe:
                dupe[aob['aob_string']] = 1
            else:
                dupe[aob['aob_string']] = 2
                self.aob_list.pop(i)

        for i in range(len(self.aob_list)-1, -1, -1):
            aob = self.aob_list[i]
            if len(aob['aob_string']) > 100:
                continue
            if aob['aob_string'] in dupe and dupe[aob['aob_string']] > 1:
                self.aob_list.pop(i)
        self.valid = len(self.aob_list)

    def has_memory_file(self):
        return self.get_memory_file().exists()

    def add_data(self, data: bytes):
        covert_data = []
        if self.data_list and len(self.data_list[-1]) == 0:
            return
        for b in data:
            covert_data.append(b)
        if len(self.data_list) == 0:
            res = {'size': len(covert_data), 'start': 0, 'aob_bytes': covert_data, 'index': 0, 'offset_from_address': 0 - self.address_offset}
            self.data_list.append([res])
            self.initial = True
            self.file_state = AOBFile.FILE_STATE_INITIAL_RESULTS
        else:
            aobs = self.compare_data(covert_data,  max_length=200)
            self.data_list.append(aobs)
            self.file_state = AOBFile.FILE_STATE_HAS_RESULTS
            if len(self.data_list[-1]) == 0:
                self.file_state = AOBFile.FILE_STATE_NO_RESULTS
            self.initial = False
            while len(self.data_list) > 3:
                self.data_list.pop(0)


    def range_aob(self, lst: list, length: int, start: int, max_wild: int):
        i = start
        stop = start+length
        if start >= stop:
            return start, stop+1, i+1
        while True:
            try:
                i = lst.index(256, i)
                if stop - i < max_wild:  # found last aob
                    i = stop - 1
                    end = i
                    while lst[end] == 256:
                        end -= 1
                    break
                if all(lst[j] == 256 for j in range(i, i + max_wild)):  # we have a row of 5 wildcards
                    end = i
                    while lst[end] == 256:
                        end -= 1
                    break
                else:
                    i += max_wild
            except ValueError:  # can't find anymore wildcards
                end = stop - 1
                i = stop
                while lst[end] == 256:
                    end -= 1
                break
        return start, end + 1, i

    def extract_aobs(self, lst: list, start:int, length: int, max_wildcards: int, min_length: int, distinct: int):
        i = start
        start_length = length
        end = start+length
        aob_list = []
        while i < end:
            while lst[i] == 256:
                i += 1
                length -= 1
                if i >= end:
                    break
            _start, _end, _index = self.range_aob(lst, length, i, max_wildcards)
            if _end - _start >= min_length:
                res_list = lst[_start: _end]
                ds = distinct + 1 if 256 in res_list else distinct
                if len(set(res_list)) >= ds:
                    aob_list.append({'start': _start, 'end': _end, 'data': res_list})
            i = _index + 1
            length = start_length - i
        return aob_list

    def compare_data(self, data: list, max_length=-1):
        old_aobs = self.data_list[-1]
        old_index = old_aobs[0]['index']
        for old_aob in old_aobs:
            start = old_aob['start']
            length = old_aob['size']
            old_data = old_aob['aob_bytes']
            j = 0
            for i in range(start, start+length):
                if data[i] != old_data[j]:
                    data[i] = 256
                j += 1
        aobs = []
        for old_aob in old_aobs:
            length = old_aob['size']
            start = old_aob['start']
            if max_length <= 0 or max_length >= length:
                aobs.append(self.extract_aobs(data, start=start, length=length, max_wildcards=4, min_length=5, distinct=3))
            else:
                while length > 0:
                    aobs.append(self.extract_aobs(data, start=start, length=min(max_length, length), max_wildcards=4, min_length=5, distinct=3))
                    length -= max_length
                    start += max_length
        all_aobs = sum(aobs, [])
        prep_aobs = []
        for aob in all_aobs:
            res = {'size': len(aob['data']), 'start': aob['start'], 'aob_bytes': aob['data'], 'index': old_index+1, 'offset_from_address': aob['start'] - self.address_offset}
            aob_string = ''
            for b in aob['data']:
                if b == 256:
                    aob_string += '?? '
                else:
                    aob_string += '{:02X} '.format(b)
            aob_string = aob_string.strip()
            res['aob_string'] = aob_string
            prep_aobs.append(res)
        return prep_aobs

    def get_data_list(self):
        return self.data_list

    def rewind(self):
        if self.data_list and len(self.data_list) > 2:
            self.data_list.pop()
            if len(self.data_list[-1]) > 0:
                self.file_state = AOBFile.FILE_STATE_HAS_RESULTS
            else:
                self.file_state = AOBFile.FILE_STATE_NO_RESULTS

    def get_name(self):
        return self.name











