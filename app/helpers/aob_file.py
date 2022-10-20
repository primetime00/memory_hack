import logging
import re
from io import BytesIO
from pathlib import Path

from app.helpers.exceptions import AOBException


class AOBFile():
    _pattern = re.compile('^Size: (\d+)\s*Offset: (-?[0-9A-F]+)\s*([0-9A-F ?]+)$')
    smallest_run = 5
    consecutive_wildcards = 5
    header = ['Process: ', 'Name: ', 'Range: ', 'Offset: ', 'Length: ', 'Valid: ']

    def __init__(self, directory: Path = Path('.aob'), filename=None):
        self.process = ""
        self.directory = directory
        self.name = ""
        self.range = 0
        self.offset = 0
        self.length = 0
        self.valid = 0
        self.final = False
        self.initial = False
        self.aob_list = []
        self.filename = filename
        if self.filename and self.directory.joinpath(self.filename).exists():
            self.read()

    def read_stream(self, handle):
        count = 0
        try:
            for line in handle.readlines():
                line = line.replace('\n', '').strip()
                if line.startswith('Process: '):
                    self.process = line[9:]
                elif line.startswith('Name: '):
                    self.name = line[6:]
                elif line.startswith('Range: '):
                    self.range = int(line[7:])
                elif line.startswith('Offset: '):
                    self.offset = int(line[8:])
                elif line.startswith('Length: '):
                    self.length = int(line[8:])
                elif line.startswith('Valid: '):
                    self.valid = int(line[7:])
                elif line.startswith('Final: '):
                    self.final = line[7:].casefold() == 'true'
                elif line.startswith('Initial: '):
                    self.initial = line[9:].casefold() == 'true'
                elif line.startswith('Size: '):
                    matches = re.match(AOBFile._pattern, line)
                    size = int(matches.group(1))
                    offset = int(matches.group(2).replace(' ', ''), 16)
                    aob = matches.group(3)
                    self.aob_list.append(self.create_aob(size, offset, aob))
                count += 1
                if count > 4 and not self.process:
                    raise AOBException('Could not parse AOB file.')
        except ValueError as e:
            raise AOBException('Could not parse AOB data [{}]'.format(e))
        except:
            raise AOBException('Could not parse AOB data')

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
        with open(path, "rt") as f:
            try:
                self.read_stream(f)
            except AOBException as e:
                raise AOBException("{} {}".format(str(path.absolute()), e.get_message()))
        self.valid = len(self.aob_list)
        self.validate()

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

    def create_aob_from_array(self, offset: int, aob_array: list):
        results = []
        aob_array, start, length = self.strip(aob_array)
        offset = offset+start
        groups = self.divide(aob_array, wildcard_length=self.consecutive_wildcards)
        if len(groups)>1:
            pass
        for item in groups:
            na_start = offset+item['start']
            if len(item['aob']) < self.smallest_run:
                continue
            res = {'size': len(item['aob']), 'offset': na_start, 'aob_string': ' '.join(item['aob']), 'aob_array': item['aob']}
            res['aob_bytes'] = [int(x, 16) if x != '??' else 256 for x in res['aob_array']]
            results.append(res)
        return results


    def add_aob_array(self, aob_array, run_start):
        aobs = self.create_aob_from_array(run_start-self.offset, aob_array)
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
        self.valid = len(self.aob_list)
        with open(path.absolute(), "wt") as f:
            try:
                f.write('Process: {}\n'.format(self.process))
                f.write('Name: {}\n'.format(self.name))
                f.write('Range: {}\n'.format(self.range))
                f.write('Offset: {}\n'.format(self.offset))
                f.write('Length: {}\n'.format(self.length))
                f.write('Valid: {}\n'.format(self.valid))
                f.write('Final: {}\n'.format(str(self.final).casefold()))
                f.write('Initial: {}\n\n'.format(str(self.initial).casefold()))
                for aob in sorted(self.aob_list, key=lambda x:x['offset']):
                    f.write("Size: {:<5} Offset: {:<15X} {}\n".format(aob['size'], aob['offset'], aob['aob_string']))
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
        for item in sorted(self.aob_list, key=lambda x: x['offset']):
            res = {'size': item['size'], 'offset': '{:X}'.format(item['offset']),
                   'aob': item['aob_string'] if item['size'] <= 50 else " ".join(item['aob_array'][0:50])}
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
        return len(self.aob_list)

    def exists(self):
        if not self.filename:
            raise AOBException('AOB file does not have a filename.')
        return self.directory.joinpath(self.filename).exists()

    def set_process(self, _process: str):
        self.process = _process

    def set_name(self, _name: str):
        self.name = _name

    def set_range(self, _range: int):
        self.range = _range

    def set_offset(self, _offset: int):
        self.offset = _offset

    def set_length(self, _length: int):
        self.length = _length

    def get_offset(self) -> int:
        return self.offset

    def get_length(self) -> int:
        return self.length

    def get_range(self) -> int:
        return self.range

    def remove_index(self, index=0):
        self.aob_list.pop(index)
        self.valid = len(self.aob_list)

    def strip(self, aob_array: list):
        aob_index = 0
        aob_list = aob_array
        while aob_list[aob_index] == '??':
            aob_index += 1
        start = aob_index
        aob_index = len(aob_list) - 1
        while aob_list[aob_index] == '??':
            aob_index -= 1
        end = aob_index
        if start == 0 and end == len(aob_list) - 1: #we didn't strip
            return aob_list, start, len(aob_list)
        else:
            aob_list = aob_list[start:end + 1]
            return aob_list, start, len(aob_list)

    def divide(self, aob_array: list, wildcard_length=5):
        pos = 0
        start = 0
        aob_groups = []
        if len(aob_array) < wildcard_length:
            aob_groups.append({'start': 0, 'aob': aob_array})
            return aob_groups
        while True:
            try:
                pos = aob_array.index('??', pos)
                if all(bt == '??' for bt in aob_array[pos:pos + wildcard_length]): #we need to divide
                    new_aob = aob_array[start:pos]
                    if len(new_aob) > 0:
                        new_aob, start2, len2 = self.strip(new_aob)
                        aob_groups.append({'start': start+start2, 'aob': new_aob})
                    start = pos+wildcard_length+1
                    pos = start
                else:
                    pos += 1
            except ValueError: #none/no more found
                new_aob = aob_array[start:]
                if len(new_aob) > 0:
                    new_aob, start2, len2 = self.strip(new_aob)
                    aob_groups.append({'start': start + start2, 'aob': new_aob})
                return aob_groups

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












