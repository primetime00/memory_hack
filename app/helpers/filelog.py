import os
from pathlib import Path

def create_log_file(dir: Path, mode):
    dir.joinpath('logs').mkdir(exist_ok=True)
    return dir.joinpath('logs').joinpath("logger-{}.log".format(os.getpid())).open(mode=mode)

def write_log(fp, txt: str):
    fp.write(txt + "\n")
    fp.flush()

def close_log_file(fp):
    fp.close()
