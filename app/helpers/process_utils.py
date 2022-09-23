import mem_edit, platform
import psutil, os, zlib

inv = ['root', 'kernoops', 'systemd-resolve', 'systemd-timesync', 'avahi', 'rtkit', 'colord', 'messagebus', 'syslog']
app = ['Isolated Web', 'WebExtensions', 'xdg-', 'Web Content', 'Socket Process', 'bwrap', 'Privileged Cont']

processed_pids = []
good_pids = []
bad_pids = []

def _is_zombied(pid):
    proc = psutil.Process(pid)
    return proc.status() == 'zombie' or not proc.is_running()

def _is_bad_proc(proc):
    if proc.status() == 'zombie':
        return True
    if platform.system() != 'Windows':
        if proc.username() in inv:
            return True
    if proc.pid == os.getpid():
        return True
    if not can_attach(proc.pid):
        return True
    name = proc.name()
    if any(sub in name for sub in app):
        return True


def get_process_list() -> {}:
    global good_pids, bad_pids
    pl = {}
    pids = mem_edit.Process.list_available_pids()

    #remove any previous good pids that might have closed
    good_pids = [x for x in good_pids if x in pids and not _is_zombied(x)]
    #remove bad pids no longer in the list
    bad_pids = [x for x in bad_pids if x in pids]

    combined_pids = good_pids + bad_pids

    #process only the other pids
    pids = [x for x in pids if x not in combined_pids]

    for pid in pids:
        proc = psutil.Process(pid)
        name = proc.name()
        if _is_bad_proc(proc):
            bad_pids.append(pid)
            continue
        good_pids.append(pid)

    for pid in good_pids:
        proc = psutil.Process(pid)
        pl[proc.name()] = pid
    return pl

def get_process_names(additional=None) -> []:
    if additional is None:
        additional = []
    else:
        additional = [x for x in additional if len(x) > 0]
    procs = list(reversed([k for k, v in get_process_list().items()]))
    procs.extend(additional)
    if len(procs) == 0:
        procs_crc = -1
    else:
        procs_crc = zlib.crc32(" ".join(sorted(procs)).encode())
    return list(set(procs)), procs_crc



def can_attach(pid):
    z = None
    try:
        z = mem_edit.Process(pid)
    except mem_edit.MemEditError:
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


def is_pid_valid(pid):
    try:
        psutil.Process(pid)
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        return False
    return True