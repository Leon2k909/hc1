"""Record a single native editor call without shell-quoting its JSON arguments."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import winreg

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
cli = str(Path(engine) / 'bin/managed/sbox-cli.exe')
label, tool = sys.argv[1:3]
args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
assert Path(label).name == label
result = subprocess.run([cli, '--call', tool, json.dumps(args)], cwd=ROOT,
                        capture_output=True, text=True, encoding='utf-8')
record = {'tool': tool, 'arguments': args, 'returncode': result.returncode,
          'stdout': result.stdout, 'stderr': result.stderr}
try:
    record['result'] = json.loads(result.stdout)
except ValueError:
    pass
for line in result.stdout.splitlines():
    p = Path(line.strip())
    if p.suffix.lower() == '.png' and p.is_file():
        target = OUT / (label + '.png')
        shutil.copy2(p, target)
        record['image'] = str(target)
(OUT / (label + '.json')).write_text(json.dumps(record, indent=2), encoding='utf-8')
if tool == 'compile_status' and record.get('result'):
    d = record['result']
    print(json.dumps({'IsBuilding': d.get('IsBuilding'), 'Compilers': [
        {k: c.get(k) for k in ('Name', 'IsBuilding', 'NeedsBuild', 'Success', 'Errors')}
        | {'Diagnostics': [v for v in c.get('Diagnostics', []) if v.get('Severity') == 'Error']}
        for c in d.get('Compilers', []) if c.get('Errors') or c.get('Name', '').startswith('verarp.')
    ]}, indent=2))
else:
    print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
raise SystemExit(result.returncode)
