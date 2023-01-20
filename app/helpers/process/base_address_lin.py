import mem_edit
import psutil


def get_process_map(process: mem_edit.Process, writeable_only=True, include_paths=[]):
    regions = []
    with open('/proc/{}/maps'.format(process.pid), 'r') as maps:
        path_map = {}
        for line in maps:
            if "/dev/dri/" in line:
                continue
            if "/dev/shm/" in line:
                continue
            if "Proton" in line:
                continue
            items = line.split()

            if len(items) < 6:
                items.append('')
            if include_paths:
                if items[5] not in include_paths:
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

