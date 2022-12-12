import os

def create_log_file():
    f = open("/tmp/bb/{}.log".format(os.getpid()), "wt")
    return f


def write_log(fp, txt: str):
    fp.write(txt + "\n")
    fp.flush()



def close_log_file(fp):
    fp.close()
