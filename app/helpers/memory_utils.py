import ctypes

import psutil


def value_to_bytes(value: str, byte_size: int):
    value = value.strip()
    if " " in value:  # assume a hex string
        res = bytes.fromhex(value.replace(" ", ""))
        return (ctypes.c_byte * len(res))(*res)
    if value.startswith('0x'):
        value = int(value[2:], 16)
    bits = byte_size * 8
    bc = int.to_bytes((int(value) + (1 << bits)) % (1 << bits), length=byte_size, byteorder='little')
    return (ctypes.c_byte * len(bc))(*bc)

def is_process_valid(pid):
    proc = psutil.Process(pid)
    return proc.is_running() and proc.status() != 'zombie'

def bytes_to_aob(bts: ctypes.Array):
    new_values = []
    for i in range(0, len(bts)):
        new_values.append('{0:0{1}X}'.format((bts[i] + (1 << 8)) % (1 << 8), 2))
    return new_values

def bytes_to_aobstr(bts: ctypes.Array):
    return " ".join(bytes_to_aob(bts))



def aob_size(aob:str, wildcard=False):
    if wildcard:
        aob = aob.replace("??", "00")
    values = aob.replace(" ", "").split('??')
    sz = 0
    for i in range(0, len(values)):
        value = values[i]
        if value == '':
            sz += 1
        else:
            byte_array = bytearray.fromhex(value)
            sz += len(byte_array)
    return sz

def value_to_hex(value: int, aob=False):
    if not aob:
        return '0x{:X}'.format(value)
    return '{0:0{1}X}'.format((value + (1 << 8)) % (1 << 8), 2)



def string_to_address(address_string: str, assume_hex=True):
    address_string = address_string.strip().replace(" ", "").lower()
    if address_string.startswith('0x'):
        address = int(address_string[2:], 16)
    elif any(elem in address_string for elem in r'abcdef') or assume_hex:
        address = int(address_string, 16)
    else:
        address = int(address_string, 10)
    return address


typeToCType = {
    ('byte_1', True):   ctypes.c_int8,
    ('byte_1', False):  ctypes.c_uint8,
    ('byte_2', True):   ctypes.c_int16,
    ('byte_2', False):  ctypes.c_uint16,
    ('byte_4', True):   ctypes.c_int32,
    ('byte_4', False):  ctypes.c_uint32,
    ('float', True):    ctypes.c_float,
    ('float', False):   ctypes.c_float,
    ('array', True):    ctypes.c_ubyte,
    ('array', False):   ctypes.c_ubyte
}