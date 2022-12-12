import ctypes

from app.helpers.exceptions import AOBException


class AOBValue:
    def __init__(self, aob_string: str):
        self.aob_search_value = None
        self._has_wildcards = False
        aob_array = aob_string.split(" ")
        self.aob_item = self.create_aob(len(aob_array), 0, aob_string)
        aob = aob_array
        best_pos = ()

        if all(x == '??' for x in aob):
            raise AOBException('Invalid AOB')

        if not any(x == '??' for x in aob):
            self.aob_search_value = (ctypes.c_byte * len(aob))(*bytes(self.aob_item['aob_bytes']))
            self.offset = 0
            return
        self._has_wildcards = True

        for i in range(0, len(aob)):
            if aob[i] not in ['00, ??']:
                st = i
                while st > 0:
                    if aob[st-1] == '??':
                        break
                    st -= 1
                ed = i+1
                while ed < len(aob):
                    if aob[ed] == '??':
                        break
                    ed += 1
                best_pos = (st, ed-st)
                break

        for i in range(0, len(aob)):
            if aob[i] not in ['00', '??', 'FF', '01']:
                st = i
                while st > 0:
                    if aob[st-1] == '??':
                        break
                    st -= 1
                ed = i+1
                while ed < len(aob):
                    if aob[ed] == '??':
                        break
                    ed += 1
                best_pos = (st, ed-st)
                break

        if not best_pos:
            for i in range(0, len(aob)):
                if aob[i] not in ['??']:
                    st = i
                    while st > 0:
                        if aob[st - 1] == '??':
                            break
                        st -= 1
                    ed = i + 1
                    while ed < len(aob):
                        if aob[ed] == '??':
                            break
                        ed += 1
                    best_pos = (st, ed - st)
                    break

        if not best_pos:
            raise AOBException('Invalid AOB')

        self.aob_search_value = (ctypes.c_ubyte * best_pos[1])(*bytes(self.aob_item['aob_bytes'][best_pos[0]:best_pos[0]+best_pos[1]]))
        self.offset = best_pos[0]

    def equal(self, other):
        arr1 = self.aob_item['aob_array']
        len1 = len(arr1)
        arr2 = other.aob_item['aob_array']
        len2 = len(arr2)
        if len1 > len2 and not all(x == '??' for x in arr1[len2:]):
            return False
        if len1 < len2 and not all(x == '??' for x in arr2[len1:]):
            return False
        for i in range(0, min(len1, len2)):
            if arr1[i] == '??' or arr2[i] == '??':
                continue
            if arr1[i] != arr2[i]:
                return False
        return True



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

    def has_wildcards(self):
        return self._has_wildcards

    def get_string(self):
        return self.aob_item['aob_string']

    def get_array(self):
        return self.aob_item['aob_array']


    @staticmethod
    def from_bytes(_bytes: bytes):
        aob_array = []
        for b in _bytes:
            aob_array.append("{:02X}".format(b))
        return AOBValue(" ".join(aob_array))






    @staticmethod
    def create_aob(size: int, offset:int, aob:str):
        res = {'size': size, 'offset': offset, 'aob_string': aob, 'aob_array': aob.split(" ")}
        res['aob_bytes'] = [int(x, 16) if x != '??' else 256 for x in res['aob_array']]
        return res