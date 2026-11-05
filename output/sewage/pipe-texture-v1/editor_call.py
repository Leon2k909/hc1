import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
CLI = r'C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe'
name = sys.argv[1]
args = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8-sig')) if len(sys.argv) > 2 else {}
result = subprocess.run([CLI, '--call', name, json.dumps(args)], capture_output=True, text=True)
(ROOT / f'{time.time_ns()}-{name}.json').write_text(result.stdout, encoding='utf-8')
print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
sys.exit(result.returncode)
