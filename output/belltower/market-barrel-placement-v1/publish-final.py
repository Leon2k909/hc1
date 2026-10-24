import subprocess
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
revision = sys.argv[1]
assert revision.startswith('r') and revision[1:].isdigit()
prefix = ['rtk', 'proxy', 'python', '-X', 'utf8']
subprocess.run(prefix + ['Tools/belltower_stage_market_barrels.py', '--revision', revision,
                        '--from-revision', 'r2'], cwd=root, check=True)
(root/'output/belltower/market-barrel-placement-v1/revision.txt').write_text(revision)
subprocess.run(prefix + ['output/knife-throw/editor_check.py', '--script',
    'output/belltower/market-barrel-placement-v1/import.cs.txt', '--output-dir',
    'output/belltower/market-barrel-placement-v1/native-import-final-'+revision,
    '--direct-call', '--cleanup-exchange', '--timeout', '60'], cwd=root, check=True)
