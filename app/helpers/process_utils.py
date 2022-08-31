import mem_edit
import psutil, os, zlib

inv = ['root', 'kernoops', 'systemd-resolve', 'systemd-timesync', 'avahi', 'rtkit', 'colord', 'messagebus', 'syslog']
app = ['Isolated Web', 'WebExtensions', 'xdg-', 'Web Content', 'Socket Process', 'bwrap', 'Privileged Cont']

def get_process_list() -> {}:
    pl = {}
    pids = mem_edit.Process.list_available_pids()
    for pid in pids:
        proc = psutil.Process(pid)
        user = proc.username()
        if user in inv:
            continue
        if pid == os.getpid():
            continue
        if not can_attach(pid):
            continue
        name = proc.name()
        if any(sub in name for sub in app):
            continue
        pl[name] = pid
    return pl

def get_process_names(additional=None) -> []:
    if additional is None:
        additional = []
    else:
        additional = [x for x in additional if len(x) > 0]
    procs = list(reversed([k for k, v in get_process_list().items()]))
    procs.extend(additional)
    procs_crc = zlib.crc32(" ".join(sorted(procs)).encode())
    return list(set(procs)), procs_crc



def can_attach(pid):
    z = None
    try:
        z = mem_edit.Process(pid)
    except Exception:
        return False
    finally:
        if z:
            z.close()
    return True

def valid_processes(proc_list):
    ps = get_process_list()
    for proc in proc_list:
        if proc in ps.keys() and can_attach(ps[proc]):
            return proc, ps[proc]
    return None, -1


