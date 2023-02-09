import os
import platform
import shutil
import stat
import subprocess
import sys
import venv
import zipfile
from pathlib import Path
from urllib import request

#run with: python3 <(wget -qO- https://github.com/primetime00/memory_hack/raw/master/app/patches/install.py)

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
    venv.create('./venv', with_pip=True)
    subprocess.check_call(['./venv/bin/python3', "-m", "pip", "install", "-r", "app/patches/requirements.txt"])

def patch_mem_edit():
    print('patching memory editor')
    master_name = 'mem_edit-master'
    dir_name = 'mem_edit/'
    dest_path = [s for s in Path('.').glob('venv/lib/**/*') if s.is_dir() and str(s).endswith('mem_edit')][0].parent

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
    with zipfile.ZipFile("app/resources/static/onsen.zip","r") as zip_ref:
        zip_ref.extractall("app/resources/static/")

def get_hostname():
    hostname = platform.node().strip()
    return hostname

def create_run_script():
    with open('run.sh', 'wt') as fp:
        fp.write("#!/bin/bash\n")
        fp.write("{} {}\n".format(Path('venv/bin/python3').absolute(), Path('memory_hack.py').absolute()))
    os.chmod('run.sh', stat.S_IRWXU)

def installed():
    app_path = Path("./app")
    prog_path = Path("./memory_hack.py")
    return app_path.exists() and prog_path.exists()

def get_sudo(service_type):
    euid = os.geteuid()
    if euid != 0:
        print("Running sudo...")
        args = ['sudo', sys.executable] + [str(Path('app/patches/install.py').absolute())] + [service_type] + [os.environ]
        os.execlpe('sudo', *args)

def run_service():
    subprocess.check_call(['/usr/bin/systemctl', "daemon-reload"])
    subprocess.check_call(['/usr/bin/systemctl', "enable", "memory_hack.service"])
    subprocess.check_call(['/usr/bin/systemctl', "start", "memory_hack.service"])

def install_service():
    print('installing service!')
    with open("app/patches/service.stub", "rt") as fp:
        data = fp.read().replace('#venv#', str(Path('venv/bin/python3').absolute())).replace('#script#', str(Path('memory_hack.py').absolute()))
    with open("/etc/systemd/system/memory_hack.service", "wt") as fp:
        fp.write(data)
    run_service()


def remove_service():
    subprocess.check_call(['/usr/bin/systemctl', "stop", "memory_hack.service"])
    subprocess.check_call(['/usr/bin/systemctl', "disable", "memory_hack.service"])
    subprocess.check_call(['/usr/bin/systemctl', "daemon-reload"])
    os.unlink("/etc/systemd/system/memory_hack.service")

def has_service():
    if Path("/etc/systemd/system/memory_hack.service").exists():
        return True
    return False

def service_running():
    stat = subprocess.call(["systemctl", "is-active", "--quiet", "memory_hack.service"])
    return stat == 0

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
    remove_service()
    Path("/etc/systemd/system/memory_hack.service").unlink(missing_ok=True)

def uninstall_files():
    shutil.rmtree(str(Path('app').absolute()))
    shutil.rmtree(str(Path('venv').absolute()))
    shutil.rmtree(str(Path('docs').absolute()))
    os.unlink(str(Path('memory_hack.py').absolute()))
    if Path('run.sh').exists():
        os.unlink(str(Path('run.sh').absolute()))
    if Path('README.md').exists():
        os.unlink(str(Path('README.md').absolute()))


def wants_service():
    return question('\nWould you like to install Memory Manipulator as a service?')

def wants_service_run():
    return question('Would you like to run the service?')

def wants_uninstall():
    return question('Would you like to uninstall Memory Manipulator?')


if '--service_install' in sys.argv:
    if os.geteuid() != 0:
        get_sudo('--service_install')
    install_service()
    print("Service installation complete.\nYou can test by accessing http://{}:5000.".format(get_hostname()))
elif '--service_remove' in sys.argv:
    if os.geteuid() != 0:
        get_sudo('--service_remove')
    uninstall_service()
    uninstall_files()
    print("Uninstall is complete!")
elif '--service_run' in  sys.argv:
    if os.geteuid() != 0:
        get_sudo('--service_run')
    print("Running service...")
    run_service()
else:
    if installed():
        print("Installation already detected.")
        if wants_uninstall():
            if has_service():
                get_sudo("--service_remove")
            else:
                uninstall_files()
                print("Uninstall is complete!")
            exit(0)
    else:
        download_source()
        download_mem_edit()
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
                if os.geteuid() != 0:
                    get_sudo('--service_run')
                    print("Service is running.\nYou can test by accessing http://{}:5000.".format(get_hostname()))
    else:
        if wants_service():
            get_sudo('--service_install')
        else:
            print("Installation complete.  You can manually start Memory Manipulator by running\n'./run.sh'")
