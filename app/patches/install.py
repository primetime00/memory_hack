import os
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

def installed():
    app_path = Path("./app")
    prog_path = Path("./mem_manip.py")
    return app_path.exists() and prog_path.exists()

def show_service():
    with open("app/patches/service.stub", "rt") as fp:
        data = fp.read().replace('#venv#', str(Path('venv').absolute())).replace('#script#', str(Path('mem_manip.py').absolute()))
        print(data)

if not installed():
    download_source()
    extract_source()
    create_venv()
    patch_mem_edit()
    extract_onsen()
show_service()
