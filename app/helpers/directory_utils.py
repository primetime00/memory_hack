from pathlib import Path
aob_directory = Path.home().joinpath('mem_manip/.aob') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/.aob')
memory_directory = Path.home().joinpath('mem_manip/.memory') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/.memory')

codes_directory = Path.home().joinpath('mem_manip/user_codes') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/user_codes')
scripts_directory = Path.home().joinpath('mem_manip/user_scripts') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/user_scripts')