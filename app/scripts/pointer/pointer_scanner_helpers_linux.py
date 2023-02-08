def add_region(process_map, region_list, region_set):
    for p in process_map:
        if 'r' not in p['privileges']:
            continue
        pathname = p['pathname']
        if pathname not in region_set:
            if len(pathname) == 0:
                region_list.append({'select': pathname, 'display': 'anonymous regions'})
            else:
                display_name = pathname
                if '/' in pathname:
                    display_name = pathname.split('/')[-1]
                region_list.append({'select': pathname, 'display': display_name})
            region_set.append(pathname)

def weigh_regions(proc_exe, region_list):
    for region in region_list:
        if region['select'].endswith(proc_exe):
            region['weight'] = 10
        elif region['select'] == '_all':
            region['weight'] = 11
        elif region['select'] == '[heap]':
            region['weight'] = 9
        elif proc_exe in region['select']:
            region['weight'] = 8
        elif region['select'].startswith('/home'):
            region['weight'] = 7
        elif region['select'].startswith('/app/bin'):
            region['weight'] = 6
        elif region['select'].startswith('/dev/shm'):
            region['weight'] = 5
        elif region['select'].startswith('/usr/bin'):
            region['weight'] = 4
        elif len(region['select']) == 0:
            region['weight'] = 3
        elif region['select'].startswith('/app'):
            region['weight'] = 2
        elif region['select'].startswith('/usr'):
            region['weight'] = 1
        else:
            region['weight'] = 0

def get_node_bounds(process_map):
    return [(x['start'], x['stop']) for x in process_map if x['inode'] != '0']

def is_heap_path(pathname: str):
    return pathname == '[heap]'

