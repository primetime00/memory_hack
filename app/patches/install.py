import os, sys, stat
import shutil
import subprocess
import zipfile
from pathlib import Path
from urllib import request

import venv

cwd = Path(os.getcwd())
zip_dir_name = 'memory_hack-master'

def download_source():
    remote_url = 'https://github.com/primetime00/memory_hack/archive/refs/heads/master.zip'
    # Define the local filename to save data
    local_file = 'master.zip'
    # Download remote and save locally
    print('downloading source')
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
    patch_path = Path("./app/patches/mem_edit.patch")
    lib_path = Path("venv/lib/python3.10/site-packages/mem_edit")
    subprocess.check_call(['/usr/bin/patch', "-p0", "-d", str(lib_path.absolute()), "-i", str(patch_path.absolute())])

def extract_onsen():
    print('extracting front-end...')
    with zipfile.ZipFile("app/resources/static/onsen.zip","r") as zip_ref:
        zip_ref.extractall("app/resources/static/")

def create_run_script():
    with open('run.sh', 'wt') as fp:
        fp.write("#!/bin/bash\n")
        fp.write("{} {}\n".format(Path('venv/bin/python3').absolute(), Path('mem_manip.py').absolute()))
    os.chmod('run.sh', stat.S_IRWXU)

def installed():
    app_path = Path("./app")
    prog_path = Path("./mem_manip.py")
    return app_path.exists() and prog_path.exists()

def get_sudo(service_type):
    euid = os.geteuid()
    if euid != 0:
        print("Running sudo...")
        args = ['sudo', sys.executable] + [str(Path('app/patches/install.py').absolute())] + [service_type] + [os.environ]
        os.execlpe('sudo', *args)

def run_service():
    subprocess.check_call(['/usr/bin/systemctl', "daemon-reload"])
    subprocess.check_call(['/usr/bin/systemctl', "enable", "mem_manip.service"])
    subprocess.check_call(['/usr/bin/systemctl', "start", "mem_manip.service"])

def install_service():
    print('installing service!')
    with open("app/patches/service.stub", "rt") as fp:
        data = fp.read().replace('#venv#', str(Path('venv/bin/python3').absolute())).replace('#script#', str(Path('mem_manip.py').absolute()))
    with open("/etc/systemd/system/mem_manip.service", "wt") as fp:
        fp.write(data)
    run_service()


def remove_service():
    subprocess.check_call(['/usr/bin/systemctl', "stop", "mem_manip.service"])
    subprocess.check_call(['/usr/bin/systemctl', "disable", "mem_manip.service"])
    subprocess.check_call(['/usr/bin/systemctl', "daemon-reload"])
    os.unlink("/etc/systemd/system/mem_manip.service")

def has_service():
    if Path("/etc/systemd/system/mem_manip.service").exists():
        return True
    return False

def service_running():
    stat = subprocess.call(["systemctl", "is-active", "--quiet", "mem_manip.service"])
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
    Path("/etc/systemd/system/mem_manip.service").unlink(missing_ok=True)

def uninstall_files():
    shutil.rmtree(str(Path('app').absolute()))
    shutil.rmtree(str(Path('venv').absolute()))
    os.unlink(str(Path('mem_manip.py').absolute()))
    if Path('run.sh').exists():
        os.unlink(str(Path('run.sh').absolute()))

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
    print("Service installation complete.\nYou can test by accessing http://localhost:5000.")
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
                    print("Service is running.\nYou can test by accessing http://localhost:5000.")
    else:
        if wants_service():
            get_sudo('--service_install')
        else:
            print("Installation complete.  You can manually start Memory Manipulator by running\n'./run.sh'")
