import ctypes
import os
import platform
import shutil
import subprocess
import sys
import time
import venv
import zipfile
from pathlib import Path
from urllib import request

#run with: powershell -Command "(new-object System.Net.WebClient).DownloadFile('https://github.com/primetime00/memory_hack/raw/master/app/patches/win_install.py','install.py')"

cwd = Path(os.getcwd())
zip_dir_name = 'memory_hack-master'

def download_source():
    remote_url = 'https://github.com/primetime00/memory_hack/archive/refs/heads/master.zip'
    # Define the local filename to save data
    local_file = 'master.zip'
    # Download remote and save locally
    print('downloading source')
    request.urlretrieve(remote_url, local_file)

def download_mem_edit():
    remote_url = 'https://github.com/primetime00/mem_edit/archive/refs/heads/master.zip'
    # Define the local filename to save data
    local_file = 'medit.zip'
    # Download remote and save locally
    request.urlretrieve(remote_url, local_file)

def download_nssm():
    remote_url = 'https://nssm.cc/release/nssm-2.24.zip'
    local_file = 'nssm.zip'
    request.urlretrieve(remote_url, local_file)

def extract_nssm():
    print('extracting nssm...')
    with zipfile.ZipFile("nssm.zip","r") as zip_ref:
        for x in zip_ref.infolist():
            if 'win64/nssm.exe' in x.filename:
                data = zip_ref.read(x)
                data_path = Path('.\\').joinpath('nssm.exe')
                data_path.write_bytes(data)

def extract_source():
    print('extracting...')
    with zipfile.ZipFile("master.zip","r") as zip_ref:
        for x in zip_ref.infolist():
            fp = x.filename.replace(zip_dir_name+'/','')
            if len(fp) == 0:
                continue
            if x.is_dir():
                os.makedirs(fp, exist_ok=True)
            else:
                data = zip_ref.read(x)
                data_path = Path(fp)
                data_path.write_bytes(data)
    os.unlink("master.zip")

def create_venv():
    print('creating virtual environment...')
    os.makedirs('venv', exist_ok=True)
    venv.create('.\\venv', with_pip=True)
    subprocess.check_call(['.\\venv\\Scripts\\python.exe', "-m", "pip", "install", "-r", "app\\patches\\requirements.txt"])

def patch_mem_edit():
    print('patching memory editor')
    master_name = 'mem_edit-master'
    dir_name = 'mem_edit/'
    dest_path = [s for s in Path('.').glob('venv\\Lib\\**\\*') if s.is_dir() and str(s).endswith('mem_edit')][0].parent

    with zipfile.ZipFile("medit.zip","r") as zip_ref:
        for x in zip_ref.infolist():
            fp = x.filename.replace(master_name+'/','')
            if len(fp) == 0:
                continue
            if dir_name not in fp:
                continue
            if x.is_dir():
                os.makedirs(fp, exist_ok=True)
            else:
                data = zip_ref.read(x)
                data_path = dest_path.joinpath(fp)
                data_path.write_bytes(data)
    os.unlink("medit.zip")
    shutil.rmtree(str(Path('mem_edit').absolute()))

def extract_onsen():
    print('extracting front-end...')
    with zipfile.ZipFile("app\\resources\\static\\onsen.zip","r") as zip_ref:
        zip_ref.extractall("app\\resources\\static\\")

def get_hostname():
    hostname = platform.node().strip()
    return hostname

def create_run_script():
    with open('run.bat', 'wt') as fp:
        fp.write("{} {}\n".format(Path('venv\\Scripts\\python.exe').absolute(), Path('memory_hack.py').absolute()))

def installed():
    app_path = Path(".\\app")
    prog_path = Path(".\\memory_hack.py")
    return app_path.exists() and prog_path.exists()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def get_sudo(service_type):
    if not is_admin():
        print("Running admin...")
        args = [str(Path('app/patches/win_install.py').absolute()), service_type]
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(args), None, 1)

def run_service():
    try:
        subprocess.check_call(["nssm.exe", "start", "MemManipService"])
    except Exception as e:
        print(e)

def install_service():
    print('installing service!')
    exe_path = Path('.\\venv\\Scripts\\python.exe').absolute()
    scr_path = Path('.\\memory_hack.py').absolute()
    try:
        subprocess.check_call(["nssm.exe", "install", "MemManipService", str(exe_path), str(scr_path)])
    except Exception as e:
        print(e)

def remove_service():
    subprocess.check_call(['/usr/bin/systemctl', "stop", "memory_hack.service"])
    subprocess.check_call(['/usr/bin/systemctl', "disable", "memory_hack.service"])
    subprocess.check_call(['/usr/bin/systemctl', "daemon-reload"])
    os.unlink("/etc/systemd/system/memory_hack.service")

def has_service():
    try:
        subprocess.check_call(["nssm.exe", "status", "MemManipService"], stderr=open(os.devnull, 'wb'), stdout=open(os.devnull, 'wb'))
        return True
    except Exception as e:
        return False

def wait_for_service_uninstall(timeout=10):
    t = time.time()
    while has_service():
        if time.time() - t > timeout:
            break
        time.sleep(0.6)
    return has_service()

def wait_for_service(timeout=10):
    t = time.time()
    while not service_running():
        if time.time() - t > timeout:
            break
        time.sleep(0.6)
    return service_running()

def service_running():
    try:
        v = subprocess.check_output(["nssm.exe", "status", "MemManipService"], stderr=open(os.devnull, 'wb')).decode('UTF-8').replace('\x00', '').strip()
        if v == 'SERVICE_STOPPED':
            return False
        return True
    except Exception as e:
        return False

def question(question):
    reply = None
    while not reply:
        reply = str(input(question + ' (y/n): ')).lower().strip()
        if reply[:1] == 'y':
            return True
        if reply[:1] == 'n':
            return False
        reply = None

def uninstall_service():
    print("Removing service...")
    try:
        subprocess.check_call(["nssm.exe", "stop", "MemManipService"])
        subprocess.check_call(["nssm.exe", "remove", "MemManipService", "confirm"])
    except Exception as e:
        print(e)

def uninstall_files():
    shutil.rmtree(str(Path('app').absolute()))
    shutil.rmtree(str(Path('venv').absolute()))
    shutil.rmtree(str(Path('docs').absolute()))
    os.unlink(str(Path('memory_hack.py').absolute()))
    if Path('run.bat').exists():
        os.unlink(str(Path('run.bat').absolute()))
    for item in Path('.\\').glob('nssm.*'):
        os.unlink(str(item.absolute()))
    if Path('README.md').exists():
        os.unlink(str(Path('README.md').absolute()))

def wants_service():
    return question('\nWould you like to install Memory Manipulator as a service?')

def wants_service_run():
    return question('Would you like to run the service?')

def wants_uninstall():
    return question('Would you like to uninstall Memory Manipulator?')

if '--service_install' in sys.argv:
    if not is_admin():
        get_sudo('--service_install')
    install_service()
    run_service()
    exit(0)
elif '--service_remove' in sys.argv:
    if not is_admin():
        get_sudo('--service_remove')
    uninstall_service()
    exit(0)
elif '--service_run' in  sys.argv:
    if os.geteuid() != 0:
        get_sudo('--service_run')
    print("Running service...")
    run_service()
    exit(0)


if installed():
    print("Installation already detected.")
    if wants_uninstall():
        if has_service():
            if not is_admin():
                print('removing service')
                get_sudo('--service_remove')
                wait_for_service_uninstall()
        uninstall_files()
        print("Uninstall is complete!")
        exit(0)
else:
    download_source()
    download_mem_edit()
    download_nssm()
    extract_nssm()
    extract_source()
    create_venv()
    patch_mem_edit()
    extract_onsen()
    create_run_script()
if has_service():
    print("Service is already installed.")
    if service_running():
        print("Service is already running.")
    else:
        print("Service is installed, but not running.")
        if wants_service_run():
            if not is_admin():
                get_sudo('--service_run')
                if not wait_for_service():
                    print("Could not run service.")
                else:
                    print("Service is running.\nYou can test by accessing http://{}:5000.".format(get_hostname()))
else:
    if wants_service():
        get_sudo('--service_install')
        if not wait_for_service():
            print("Could not run/install service.")
        else:
            print("Service is running.\nYou can test by accessing http://{}:5000.".format(get_hostname()))
    else:
        print("Installation complete.  You can manually start Memory Manipulator by running\n'run.bat'")

