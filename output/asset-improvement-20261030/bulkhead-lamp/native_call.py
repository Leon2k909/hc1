"""Attach to the existing editor; JSON travels as data, avoiding PS5 quoting."""
import json, os, subprocess, sys, winreg
from pathlib import Path
engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
args = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
result = subprocess.run([str(Path(engine)/'bin/managed/sbox-cli.exe'), '--call', sys.argv[1], json.dumps(args)], capture_output=True, text=True)
if sys.argv[1]=='search_tools' and result.returncode==0:
    catalog=json.loads(result.stdout)
    Path(__file__).with_name('native-tools.json').write_text(json.dumps(catalog,indent=2))
    print(json.dumps([t for t in catalog.get('tools',[]) if t.get('name','').startswith('bridge_')],indent=2))
else:
    print(result.stdout)
if result.stderr: print(result.stderr, file=sys.stderr)
sys.exit(result.returncode)
