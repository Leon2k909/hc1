import argparse
import json
import os
from pathlib import Path
import subprocess
import winreg

parser=argparse.ArgumentParser()
parser.add_argument('tool')
parser.add_argument('--script',type=Path)
parser.add_argument('--args',type=Path)
parser.add_argument('--timeout',type=int,default=300)
parser.add_argument('--output',type=Path)
options=parser.parse_args()
engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
        engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
arguments=json.loads(options.args.read_text(encoding='utf-8')) if options.args else {}
if options.script:
    arguments={'path':str(options.script.resolve())}
command=['rtk',str(Path(engine)/'bin/managed/sbox-cli.exe'),'--request-timeout',str(options.timeout),'--call',options.tool,json.dumps(arguments)]
result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace')
if options.output:
    options.output.write_text(result.stdout,encoding='utf-8')
    print(f'Exit {result.returncode}; result saved to {options.output}')
else:
    print(result.stdout)
if result.stderr:
    print(result.stderr)
raise SystemExit(result.returncode)
