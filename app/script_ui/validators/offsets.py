import re

regex_offsets = r'^\d+(, ?\d+)*$'
def offsets_match(txt: str):
    return re.match(regex_offsets, txt.upper().strip(), re.IGNORECASE)


