
class TrendBreak(Exception):
    pass

def fix_trend_list(trend_list: list):
    nt = []
    current = None
    for t in trend_list:
        if t != current:
            current = t
            nt.append(t)
    return nt

def find_trends(data: list):
    tl = []
    ol = data.copy()
    while True:
        if len(ol) <= 1:
            return tl
        elif len(ol) == 2:
            if ol[0] == ol[1]:
                tl.append('flat')
            elif ol[0] > ol[1]:
                tl.append('down')
            else:
                tl.append('up')
            return tl
        else:
            if ol[0] == ol[1]: #flat
                tl.append('flat')
                try:
                    res = ol.index(list(filter(lambda i: i != ol[0], ol))[0])
                except IndexError:
                    return tl
                ol = ol[res-1:]
            elif ol[0] < ol[1]: #incline or up
                if ol[1] < ol[2]: #this is an incline
                    tl.append('incline')
                    res = 0
                    for i in range(0, len(ol) - 1):
                        if ol[i + 1] > ol[i]:
                            res += 1
                        else:
                            break
                    ol = ol[res:]
                else: #spike up ol[2] == ol[1] or ol[2] < ol[1]
                    tl.append('up')
                    ol.pop(0)
            elif ol[0] > ol[1]: #decline or down
                if ol[1] > ol[2]: #this is an decline
                    tl.append('decline')
                    res = 0
                    for i in range(0, len(ol)-1):
                        if ol[i+1] < ol[i]:
                            res += 1
                        else:
                            break
                    ol = ol[res:]
                else: #spike down ol[2] == ol[1] or ol[2] > ol[1]
                    tl.append('down')
                    ol.pop(0)

def calculate_trend(trend_list: list, data: dict) -> list:
    valid_keys = []
    for key in sorted(data.keys()):
        tl = find_trends(data[key])
        ol = tl.copy()
        dl = trend_list.copy()
        match_percent = 1.0
        while True:
            if len(ol) == 0:
                break
            if dl == ol:
                valid_keys.append((key, match_percent))
                break
            else:
                if ol[0] == 'flat':
                    ol.pop(0)
                    if dl[0] != 'flat':
                        match_percent -= 0.1
                    else:
                        dl.pop(0)
                    continue
                elif ol[-1] == 'flat':
                    ol.pop()
                    if dl[-1] != 'flat':
                        match_percent -= 0.1
                    else:
                        dl.pop()
                    continue
                if 'incline' not in dl and 'incline' in ol:
                    ol = list(map(lambda x: x.replace('incline', 'up'), ol))
                    match_percent -= 0.1
                    continue
                elif 'decline' not in dl and 'decline' in ol:
                    ol = list(map(lambda x: x.replace('decline', 'down'), ol))
                    match_percent -= 0.1
                    continue
                if 'flat' not in dl and 'incline' not in ol and 'decline' not in ol and 'flat' in ol:
                    ol = [x for x in ol if x != 'flat']
                    match_percent -= 0.1
                else:
                    break
    valid_keys.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in valid_keys]

def calculate_trend2(trend_list: list, data: dict) -> list:
    valid_keys = []
    original_trend_list = fix_trend_list(trend_list)
    for key in sorted(data.keys()):
        trend_list = original_trend_list.copy()
        data_row = data[key].copy()
        data_index = 0
        trend_index = 0
        count = 0
        try:
            while True:
                if not trend_list and len(data_row) > 0:
                    raise TrendBreak()
                if len(data_row) == 1:
                    if len(trend_list) > 1 and not all(x == trend_list[0] for x in trend_list):
                        raise TrendBreak()
                    else:
                        valid_keys.append(key)
                        break
                current_value = data_row[data_index]
                next_value = data_row[data_index + 1] if data_index + 1 < len(data_row) else None
                t = trend_list[trend_index]
                if t == 'up':
                    if next_value >= current_value:
                        data_row.pop(0)
                        count += 1
                    else:
                        if count == 0:
                            raise TrendBreak()
                        trend_list.pop(0)
                        count = 0
                elif t == 'down':
                    if next_value <= current_value:
                        data_row.pop(0)
                        count += 1
                    else:
                        if count == 0:
                            raise TrendBreak()
                        trend_list.pop(0)
                        count = 0
                else:
                    if next_value != current_value:  # we are no longer equal
                        trend_list.pop(0)
                        count = 0
                    else:
                        data_row.pop(0)
                        count += 1
        except TrendBreak:
            pass
    return valid_keys