import re

regex_address = '^[0-9A-F]{5,16}$'
def address_match(txt: str):
    return re.match(regex_address, txt.upper().strip(), re.IGNORECASE)


