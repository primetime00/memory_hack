import platform
if platform.system() == 'Linux':
    from .pointer_scanner_helpers_linux import *
else:
    from .pointer_scanner_helpers_windows import *
