"""Native CLI call with shell-safe JSON arguments and optional compact diagnostics."""
import json
import os
from pathlib import Path
import subprocess
import sys
import winreg

engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
cli = str(Path(engine)/'bin/managed/sbox-cli.exe')
tool = sys.argv[1]
arguments = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else None
command = [cli, '--call', tool]
if arguments is not None:
    command.append(json.dumps(arguments))
result = subprocess.run(command, capture_output=True, text=True)
if result.stderr:
    print(result.stderr, file=sys.stderr, end='')
if tool=='compile_status' and result.returncode==0:
    data=json.loads(result.stdout)
    print(json.dumps({'IsBuilding':data['IsBuilding'], 'Compilers':[
        {k:c[k] for k in ('Name','IsBuilding','NeedsBuild','Success','Errors')} |
        {'Diagnostics':[d for d in c.get('Diagnostics',[]) if d['Severity']=='Error']}
        for c in data['Compilers'] if c['Name'].startswith('verarp.') or c['Errors']]},indent=2))
else:
    print(result.stdout, end='')
raise SystemExit(result.returncode)
