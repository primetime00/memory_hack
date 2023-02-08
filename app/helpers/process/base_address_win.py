import ctypes
import ctypes.wintypes

import mem_edit
import psutil
import fnmatch

# Process handle privileges
privileges = {
    'PROCESS_QUERY_INFORMATION': 0x0400,
    'PROCESS_VM_OPERATION': 0x0008,
    'PROCESS_VM_READ': 0x0010,
    'PROCESS_VM_WRITE': 0x0020,
    }
privileges['PROCESS_RW'] = (
    privileges['PROCESS_QUERY_INFORMATION'] |
    privileges['PROCESS_VM_OPERATION'] |
    privileges['PROCESS_VM_READ'] |
    privileges['PROCESS_VM_WRITE']
    )

# Memory region states
mem_states = {
    'MEM_COMMIT': 0x1000,
    'MEM_FREE': 0x10000,
    'MEM_RESERVE': 0x2000,
    }

# Memory region permissions
page_protections = {
    'PAGE_EXECUTE': 0x10,
    'PAGE_EXECUTE_READ': 0x20,
    'PAGE_EXECUTE_READWRITE': 0x40,
    'PAGE_EXECUTE_WRITECOPY': 0x80,
    'PAGE_NOACCESS': 0x01,
    'PAGE_READWRITE': 0x04,
    'PAGE_WRITECOPY': 0x08,
    }
# Custom (combined) permissions
page_protections['PAGE_READABLE'] = (
    page_protections['PAGE_EXECUTE_READ'] |
    page_protections['PAGE_EXECUTE_READWRITE'] |
    page_protections['PAGE_READWRITE']
    )
page_protections['PAGE_READWRITEABLE'] = (
    page_protections['PAGE_EXECUTE_READWRITE'] |
    page_protections['PAGE_READWRITE']
    )
page_protections['PAGE_EXECUTABLE'] = (
    page_protections['PAGE_EXECUTE_READ'] |
    page_protections['PAGE_EXECUTE_READWRITE'] |
    page_protections['PAGE_EXECUTE_WRITECOPY']
    )

# Memory types
mem_types = {
    'MEM_IMAGE': 0x1000000,
    'MEM_MAPPED': 0x40000,
    'MEM_PRIVATE': 0x20000,
    }


# C struct for VirtualQueryEx
class MEMORY_BASIC_INFORMATION32(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.wintypes.DWORD),
        ('AllocationBase', ctypes.wintypes.DWORD),
        ('AllocationProtect', ctypes.wintypes.DWORD),
        ('RegionSize', ctypes.wintypes.DWORD),
        ('State', ctypes.wintypes.DWORD),
        ('Protect', ctypes.wintypes.DWORD),
        ('Type', ctypes.wintypes.DWORD),
        ]

class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_ulonglong),
        ('AllocationBase', ctypes.c_ulonglong),
        ('AllocationProtect', ctypes.wintypes.DWORD),
        ('__alignment1', ctypes.wintypes.DWORD),
        ('RegionSize', ctypes.c_ulonglong),
        ('State', ctypes.wintypes.DWORD),
        ('Protect', ctypes.wintypes.DWORD),
        ('Type', ctypes.wintypes.DWORD),
        ('__alignment2', ctypes.wintypes.DWORD),
        ]

PTR_SIZE = ctypes.sizeof(ctypes.c_void_p)
if PTR_SIZE == 8:       # 64-bit python
    MEMORY_BASIC_INFORMATION = MEMORY_BASIC_INFORMATION64
elif PTR_SIZE == 4:     # 32-bit python
    MEMORY_BASIC_INFORMATION = MEMORY_BASIC_INFORMATION32

GetMappedFileName = ctypes.windll.psapi.GetMappedFileNameW
GetMappedFileName.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPVOID, ctypes.wintypes.LPWSTR, ctypes.wintypes.DWORD]
GetMappedFileName.restype = ctypes.wintypes.DWORD

ctypes.windll.kernel32.VirtualQueryEx.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPCVOID,
    ctypes.c_void_p,
    ctypes.c_size_t]
ctypes.windll.kernel32.ReadProcessMemory.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPCVOID,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p]
ctypes.windll.kernel32.WriteProcessMemory.argtypes = [
    ctypes.wintypes.HANDLE,
    ctypes.wintypes.LPCVOID,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.c_void_p]


# C struct for GetSystemInfo
class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ('wProcessorArchitecture', ctypes.wintypes.WORD),
        ('wReserved', ctypes.wintypes.WORD),
        ('dwPageSize', ctypes.wintypes.DWORD),
        ('lpMinimumApplicationAddress', ctypes.c_void_p),
        ('lpMaximumApplicationAddress', ctypes.c_void_p),
        ('dwActiveProcessorMask', ctypes.c_void_p),
        ('dwNumberOfProcessors', ctypes.wintypes.DWORD),
        ('dwProcessorType', ctypes.wintypes.DWORD),
        ('dwAllocationGranularity', ctypes.wintypes.DWORD),
        ('wProcessorLevel', ctypes.wintypes.WORD),
        ('wProcessorRevision', ctypes.wintypes.WORD),
        ]



def get_process_map(process: mem_edit.Process, writeable_only=True, include_paths=[]):
    sys_info = SYSTEM_INFO()
    sys_info_ptr = ctypes.byref(sys_info)
    ctypes.windll.kernel32.GetSystemInfo(sys_info_ptr)

    start = sys_info.lpMinimumApplicationAddress
    stop = sys_info.lpMaximumApplicationAddress
    path_map = {}

    def get_mem_info(address):
        """
        Query the memory region starting at or before 'address' to get its size/type/state/permissions.
        """
        mbi = MEMORY_BASIC_INFORMATION()
        mbi_ptr = ctypes.byref(mbi)
        mbi_size = ctypes.sizeof(mbi)

        success = ctypes.windll.kernel32.VirtualQueryEx(
            process.process_handle,
            address,
            mbi_ptr,
            mbi_size)

        if success != mbi_size:
            if success == 0:
                raise mem_edit.MemEditError('Failed VirtualQueryEx with handle ' +
                                   '{}: {}'.format(process.process_handle, ctypes.get_last_error()))
            else:
                raise mem_edit.MemEditError('VirtualQueryEx output too short!')

        return mbi

    regions = []
    page_ptr = start
    while page_ptr < stop:
        page_info = get_mem_info(page_ptr)
        mem_type_valid = page_info.Type == mem_types['MEM_PRIVATE'] or page_info.Type == mem_types[
            'MEM_MAPPED'] or page_info.Type == mem_types['MEM_IMAGE']
        mem_state_comitted = page_info.State == mem_states['MEM_COMMIT']
        mem_readable = page_info.Protect & page_protections['PAGE_READABLE'] != 0
        mem_writable = page_info.Protect & page_protections['PAGE_READWRITEABLE'] != 0
        mem_executable = page_info.Protect & page_protections['PAGE_EXECUTABLE'] != 0

        if not (mem_type_valid and mem_state_comitted and mem_readable):
            page_ptr += page_info.RegionSize
            continue

        image_filename = ctypes.create_unicode_buffer(u"", 260)
        GetMappedFileName(process.process_handle, page_ptr, image_filename, 260)
        pathname = image_filename.value if len(image_filename.value) > 0 else ' '

        item_map = {
            'bounds': "{:x}-{:x}".format(page_ptr, page_ptr + page_info.RegionSize),
            'privileges': "{}{}{}{}".format('r' if mem_readable else '-', 'w' if mem_writable else '-', 'x' if mem_executable else '-', 'p'),
            'offset': "{:x}".format(page_info.AllocationBase),
            'dev': '0',
            'inode': '0',
            'pathname': pathname,
        }

        if item_map['pathname'] not in path_map:
            path_map[item_map['pathname']] = 0
        else:
            path_map[item_map['pathname']] += 1

        if not mem_writable and writeable_only:
            page_ptr += page_info.RegionSize
            continue

        if include_paths:
            if pathname not in include_paths:
                page_ptr += page_info.RegionSize
                continue

        if mem_edit.Process.blacklist:
            if any(fnmatch.fnmatch(pathname, x) for x in mem_edit.Process.blacklist):
                continue

        item_map['start'] = page_ptr
        item_map['stop'] = page_ptr + page_info.RegionSize
        item_map['size'] = page_info.RegionSize
        item_map['map_index'] = path_map[item_map['pathname']]
        regions.append(item_map)
        page_ptr += page_info.RegionSize
    return regions

def get_base_address(process: mem_edit.Process):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    proc = psutil.Process(process.pid)
    exe = proc.exe()
    for p in pm:
        if p['pathname'] == exe:
            return p['start']
    return -1

def get_address_base(process: mem_edit.Process, address):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    for p in pm:
        if p['start'] <= address <= p['stop']:
            return p
    return None

def get_address_path(process: mem_edit.Process, address: int):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    for p in pm:
        if p['start'] <= address <= p['stop']:
            if '\\' not in p['pathname']:
                return None
            offset = address - p['start']
            stem = p['pathname'].split('\\')[-1]
            index = p['map_index']
            return '{}:{}+{:X}'.format(stem, index, offset)
    return None

def get_path_address(process: mem_edit.Process, path: str):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    if ':' in path:
        path = path.strip()
        pn = path.split(':')[0]
        index = path.split(':')[1].split('+')[0]
        offset = path.split(':')[1].split('+')[1]
        for proc in pm:
            if proc['pathname'].endswith(pn) and proc['map_index'] == int(index):
                res = proc['start'] + int(offset, 16)
                return res
        return None
    else:
        return int(path, 16)
