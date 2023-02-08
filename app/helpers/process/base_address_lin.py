import mem_edit
import psutil
import fnmatch


def get_process_map(process: mem_edit.Process, writeable_only=True, include_paths=[]):
    regions = []
    with open('/proc/{}/maps'.format(process.pid), 'r') as maps:
        path_map = {}
        for line in maps:
            if "/dev/dri/" in line:
                continue
            if "Proton" in line:
                continue
            items = line.split()

            if len(items) < 6:
                items.append('')
            if len(items) >= 7:
                items[5] = " ".join(items[5:])

            if include_paths:
                if items[5] not in include_paths:
                    continue

            if mem_edit.Process.blacklist:
                if any(fnmatch.fnmatch(items[5], x) for x in mem_edit.Process.blacklist):
                    continue


            item_map = {
                'bounds': items[0],
                'privileges': items[1],
                'offset': items[2],
                'dev': items[3],
                'inode': items[4],
                'pathname': items[5] if len(items) >= 6 else "",
            }

            if item_map['pathname'] not in path_map:
                path_map[item_map['pathname']] = 0
            else:
                path_map[item_map['pathname']] += 1

            if 'r' not in item_map['privileges']:
                continue

            if writeable_only and 'w' not in item_map['privileges']:
                continue

            start, stop = (int(bound, 16) for bound in item_map['bounds'].split('-'))
            item_map['start'] = start
            item_map['stop'] = stop
            item_map['size'] = stop-start
            item_map['map_index'] = path_map[item_map['pathname']]
            regions.append(item_map)
    return regions

def get_base_address(process: mem_edit.Process):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    proc = psutil.Process(process.pid)
    exe = proc.exe()
    for p in pm:
        if p['pathname'] == exe:
            return p['start']
    return -1

def get_address_base(process: mem_edit.Process, address: int):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    for p in pm:
        if p['start'] <= address <= p['stop']:
            return p
    return None

def get_address_path(process: mem_edit.Process, address: int):
    pm = sorted(get_process_map(process, writeable_only=False), key=lambda x: x['start'])
    for p in pm:
        if p['start'] <= address <= p['stop']:
            if '/' not in p['pathname']:
                return None
            offset = address - p['start']
            stem = p['pathname'].split('/')[-1]
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


