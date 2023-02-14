import platform

from .main import Pointer
from .pointer_offset_script import PointerOffset
from .pointer_scanner_script import PointerScanner
from .pointer_verify_script import PointerVerify

if platform.system() == 'Linux':
    from .pointer_scanner_helpers_linux import add_region, weigh_regions, get_node_bounds, is_heap_path
else:
    from .pointer_scanner_helpers_windows import add_region, weigh_regions, get_node_bounds, is_heap_path
