from pathlib import Path

base_directory = Path.home().joinpath('memory_hack') if '/root' not in str(Path.home()) else Path('/opt/memory_hack')
aob_directory = Path.home().joinpath('memory_hack/.aob') if '/root' not in str(Path.home()) else Path('/opt/memory_hack/.aob')
memory_directory = Path.home().joinpath('memory_hack/.memory') if '/root' not in str(Path.home()) else Path('/opt/memory_hack/.memory')

codes_directory = Path.home().joinpath('memory_hack/user_codes') if '/root' not in str(Path.home()) else Path('/opt/memory_hack/user_codes')
scripts_directory = Path.home().joinpath('memory_hack/user_scripts') if '/root' not in str(Path.home()) else Path('/opt/memory_hack/user_scripts')
scripts_memory_directory = Path.home().joinpath('memory_hack/user_scripts/.memory') if '/root' not in str(Path.home()) else Path('/opt/memory_hack/user_scripts/.memory')


base_directory.mkdir(exist_ok=True)
aob_directory.mkdir(exist_ok=True)
memory_directory.mkdir(exist_ok=True)
codes_directory.mkdir(exist_ok=True)
scripts_directory.mkdir(exist_ok=True)
scripts_memory_directory.mkdir(exist_ok=True)