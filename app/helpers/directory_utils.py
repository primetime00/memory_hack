from pathlib import Path

base_directory = Path.home().joinpath('mem_manip') if '/root' not in str(Path.home()) else Path('/opt/mem_manip')
aob_directory = Path.home().joinpath('mem_manip/.aob') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/.aob')
memory_directory = Path.home().joinpath('mem_manip/.memory') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/.memory')

codes_directory = Path.home().joinpath('mem_manip/user_codes') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/user_codes')
scripts_directory = Path.home().joinpath('mem_manip/user_scripts') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/user_scripts')
scripts_memory_directory = Path.home().joinpath('mem_manip/user_scripts/.memory') if '/root' not in str(Path.home()) else Path('/opt/mem_manip/user_scripts/.memory')


base_directory.mkdir(exist_ok=True)
aob_directory.mkdir(exist_ok=True)
memory_directory.mkdir(exist_ok=True)
codes_directory.mkdir(exist_ok=True)
scripts_directory.mkdir(exist_ok=True)
scripts_memory_directory.mkdir(exist_ok=True)