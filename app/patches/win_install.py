import ctypes
import os
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
    subprocess.check_call(['.\\venv\\Scripts\\python.exe', "-m", "pip", "install", "patch"])


def patch_mem_edit():
    print('patching memory editor')
    patch_path = Path(".\\app\\patches\\mem_edit.patch")
    lib_path = Path("venv\\Lib\\site-packages\\mem_edit")
    subprocess.call(['.\\venv\\Scripts\\python.exe', "-m", "patch", "-p0", "-d", str(lib_path.absolute()), str(patch_path.absolute())])

def extract_onsen():
    print('extracting front-end...')
    with zipfile.ZipFile("app\\resources\\static\\onsen.zip","r") as zip_ref:
        zip_ref.extractall("app\\resources\\static\\")

def create_run_script():
    with open('run.bat', 'wt') as fp:
        fp.write("{} {}\n".format(Path('venv\\Scripts\\python.exe').absolute(), Path('mem_manip.py').absolute()))

def installed():
    app_path = Path(".\\app")
    prog_path = Path(".\\mem_manip.py")
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
    scr_path = Path('.\\mem_manip.py').absolute()
    try:
        subprocess.check_call(["nssm.exe", "install", "MemManipService", str(exe_path), str(scr_path)])
    except Exception as e:
        print(e)

def remove_service():
    subprocess.check_call(['/usr/bin/systemctl', "stop", "mem_manip.service"])
    subprocess.check_call(['/usr/bin/systemctl', "disable", "mem_manip.service"])
    subprocess.check_call(['/usr/bin/systemctl', "daemon-reload"])
    os.unlink("/etc/systemd/system/mem_manip.service")

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
    os.unlink(str(Path('mem_manip.py').absolute()))
    if Path('run.bat').exists():
        os.unlink(str(Path('run.bat').absolute()))
    for item in Path('.\\').glob('nssm.*'):
        os.unlink(str(item.absolute()))


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
                    print("Service is running.\nYou can test by accessing http://localhost:5000.")
else:
    if wants_service():
        get_sudo('--service_install')
        if not wait_for_service():
            print("Could not run/install service.")
        else:
            print("Service is running.\nYou can test by accessing http://localhost:5000.")
    else:
        print("Installation complete.  You can manually start Memory Manipulator by running\n'run.bat'")

