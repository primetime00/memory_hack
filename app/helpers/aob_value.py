import ctypes

from app.helpers.exceptions import AOBException

class AOBValue:
    def __init__(self, aob_string: str):
        self.aob_search_value = None
        aob_array = aob_string.split(" ")
        self.aob_item = self.create_aob(len(aob_array), 0, aob_string)
        aob = aob_array
        best_pos = -1

        if all(x == '??' for x in aob):
            raise AOBException('Invalid AOB')

        for i in range(0, len(aob)):
            if aob[i] not in ['00, ??']:
                best_pos = i
                break

        for i in range(0, len(aob)):
            if aob[i] not in ['00', '??', 'FF', '01']:
                best_pos = i
                break

        if best_pos == -1:
            for i in range(0, len(aob)):
                if aob[i] not in ['??']:
                    best_pos = i

        if best_pos == -1:
            raise AOBException('Invalid AOB')

        self.aob_search_value = ctypes.c_ubyte(int(aob[best_pos], 16))
        self.offset = best_pos

    def cmp(self, *args):
        mem = args[0]
        cap = args[1]
        user = args[2]
        for i in range(0, self.aob_item['size']):
            bt = self.aob_item['aob_bytes'][i]
            if bt >= 256:
                continue
            if bt != mem[i]:
                return False
        return True

    def get_search_value(self):
        return self.aob_search_value

    def get_offset(self):
        return self.offset


    @staticmethod
    def create_aob(size: int, offset:int, aob:str):
        res = {'size': size, 'offset': offset, 'aob_string': aob, 'aob_array': aob.split(" ")}
        res['aob_bytes'] = [int(x, 16) if x != '??' else 256 for x in res['aob_array']]
        return res