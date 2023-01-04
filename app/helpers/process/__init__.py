import platform

system = platform.system()
if system == 'Windows':
    from .base_address_win import *
elif system == 'Linux':
    from .base_address_lin import *
else:
    raise Exception('Only Linux and Windows are currently supported.')
from .converter import BaseConvert
