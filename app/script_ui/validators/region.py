import re

regex_region = r'^((?!(?:COM[0-9]|CON|LPT[0-9]|NUL|PRN|AUX|com[0-9]|con|lpt[0-9]|nul|prn|aux)|\s|[\.]{2,})[^\\\/:*"?<>|]{1,254}(?<![\s\.])):(\d+)\+([0-9a-f]+)$'
def region_match(txt: str):
    return re.match(regex_region, txt.strip(), re.IGNORECASE)


