from pathlib import Path

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
                if '\\' in pathname:
                    display_name = pathname.split('\\')[-1]
                region_list.append({'select': pathname, 'display': display_name})
            region_set.append(pathname)

def weigh_regions(proc_exe, region_list):
    stem = ''
    if Path(proc_exe).exists():
        proc_exe = Path(proc_exe).name
        stem = Path(proc_exe).stem
    proc_exe = proc_exe.lower()
    for region in region_list:
        if region['select'].endswith(proc_exe):
            region['weight'] = 10
        elif region['select'] == '_all':
            region['weight'] = 11
        elif len(region['select']) == 0 or region['select'] == ' ':
            region['weight'] = 9

        elif region['select'].lower().endswith('.drv'):
            region['weight'] = 2

        elif proc_exe in region['select'].lower():
            region['weight'] = 9

        elif stem and stem in region['select'].lower():
            sections = region['select'].lower().split('\\')
            stem_location = sections.index(stem)
            if (len(sections) - 1) - stem_location > 1:
                region['weight'] = 8
            else:
                region['weight'] = 7
        elif 'Users' in region['select']:
            region['weight'] = 6
        else:
            region['weight'] = 1


def get_node_bounds(process_map):
    return [(x['start'], x['stop']) for x in process_map if len(x['pathname']) > 1]

def is_heap_path(pathname: str):
    return pathname == ' '

