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
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != 'zombie'
    except psutil.NoSuchProcess:
        return False

def bytes_to_aob(bts: ctypes.Array):
    new_values = []
    for i in range(0, len(bts)):
        new_values.append('{0:0{1}X}'.format((bts[i] + (1 << 8)) % (1 << 8), 2))
    return new_values

def bytes_to_aobstr(bts: ctypes.Array):
    return " ".join(bytes_to_aob(bts))

def bytes_to_printable_value(bts: bytes, size: str, signed: bool=True):
    if size == 'byte_1':
        ct =  ctypes.c_int8 if signed else ctypes.c_uint8
    elif size == 'byte_2':
        ct = ctypes.c_int16 if signed else ctypes.c_uint16
    elif size == 'byte_4':
        ct = ctypes.c_int32 if signed else ctypes.c_uint32
    elif size == 'byte_8':
        ct =  ctypes.c_int64 if signed else ctypes.c_uint64
    elif size == 'float':
        ct = ctypes.c_float
    else:
        ct = ctypes.c_ubyte
    buf = (ct*1)()
    ctypes.memmove(ctypes.pointer(buf), bts, len(bts))
    return str(buf[0])



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

def get_ctype(value: str, size: str):
    if size == 'byte_1':
        return ctypes.c_int8 if int(value) < 128 else ctypes.c_uint8
    elif size == 'byte_2':
        return ctypes.c_int16 if int(value) < 32768 else ctypes.c_uint16
    elif size == 'byte_4':
        return ctypes.c_int32 if int(value) < 2147483648 else ctypes.c_uint32
    elif size == 'byte_8':
        return ctypes.c_int64 if int(value) < 9223372036854775808 else ctypes.c_uint64
    elif size == 'float':
        return ctypes.c_float
    return ctypes.c_ubyte

def get_ctype_from_size(size: str):
    if size == 'byte_1':
        return (ctypes.c_byte*1)()
    elif size == 'byte_2':
        return (ctypes.c_byte*2)()
    elif size == 'byte_4':
        return (ctypes.c_byte*4)()
    elif size == 'byte_8':
        return (ctypes.c_byte*8)()
    elif size == 'float':
        return (ctypes.c_byte*4)()
    return (ctypes.c_byte*1)()

def get_ctype_from_buffer(buffer: ctypes.Array, size: str, signed: bool):
    if size == 'byte_2':
        return ctypes.c_int16.from_buffer(buffer) if signed else ctypes.c_uint16.from_buffer(buffer)
    elif size == 'byte_4':
        return ctypes.c_int32.from_buffer(buffer) if signed else ctypes.c_uint32.from_buffer(buffer)
    elif size == 'byte_8':
        return ctypes.c_int64.from_buffer(buffer) if signed else ctypes.c_uint64.from_buffer(buffer)
    elif size == 'float':
        return ctypes.c_float.from_buffer(buffer)
    else:
        return ctypes.c_int8.from_buffer(buffer) if signed else ctypes.c_uint8.from_buffer(buffer)

def get_ctype_from_int_value(value:int, size:str, signed: bool):
    if size == 'byte_2':
        return ctypes.c_int16(value) if signed else ctypes.c_uint16(value)
    elif size == 'byte_4':
        return ctypes.c_int32(value) if signed else ctypes.c_uint32(value)
    elif size == 'byte_8':
        return ctypes.c_int64(value) if signed else ctypes.c_uint64(value)
    else:
        return ctypes.c_int8(value) if signed else ctypes.c_uint8(value)



def limit(value, size:str):
    if size == 'byte_1':
        return min(value, 255)
    elif size == 'byte_2':
        return min(value, 65535)
    elif size == 'byte_4':
        return min(value, 4294967295)
    elif size == 'byte_8':
        return min(value, 18446744073709551616)
    else:
        return value







typeToCType = {
    ('byte_1', True):   ctypes.c_int8,
    ('byte_1', False):  ctypes.c_uint8,
    ('byte_2', True):   ctypes.c_int16,
    ('byte_2', False):  ctypes.c_uint16,
    ('byte_4', True):   ctypes.c_int32,
    ('byte_4', False):  ctypes.c_uint32,
    ('byte_8', True):   ctypes.c_int64,
    ('byte_8', False):  ctypes.c_uint64,
    ('float', True):    ctypes.c_float,
    ('float', False):   ctypes.c_float,
    ('array', True):    ctypes.c_ubyte,
    ('array', False):   ctypes.c_ubyte
}