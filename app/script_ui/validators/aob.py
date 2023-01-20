import re

regex_aob = r'^(([A-F0-9]{2}|\?{2})\s)*([A-F0-9]{2}|\?{2})$'
def aob_match(txt: str):
    return re.match(regex_aob, txt.strip(), re.IGNORECASE)


