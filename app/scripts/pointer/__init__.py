import platform

from .main import Pointer
from .pointer_offset_script import PointerOffset
from .pointer_scanner_script import PointerScanner
from .pointer_verify_script import PointerVerify

if platform.system() == 'Linux':
    from .pointer_scanner_helpers_linux import *
else:
    from .pointer_scanner_helpers_windows import *
