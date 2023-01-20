import platform
if platform.system() == 'Linux':
    from .pointer_scanner_helpers_linux import add_region, is_heap_path, weigh_regions, get_node_bounds
else:
    from .pointer_scanner_helpers_windows import add_region, is_heap_path, weigh_regions, get_node_bounds
