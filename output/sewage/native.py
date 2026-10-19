"""Short-lived native s&box calls; attach only, never launch or restart."""
import json, os, subprocess, sys, winreg, shutil
from pathlib import Path

engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
        engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
settings=json.loads(Path('output/sewage/native.json').read_text())
name=sys.argv[1]
args=json.loads(sys.argv[2]) if len(sys.argv)>2 and name!='run' else {}
if name=='run':
    source=Path('Sources/Sewage/editor')/(sys.argv[2]+'.cs.txt')
    if not source.exists():source=Path('output/sewage')/(sys.argv[2]+'.cs.txt')
    exchange=Path(settings['exchange']);exchange.mkdir(parents=True,exist_ok=True)
    script=exchange/('sewage-'+source.name)
    shutil.copy2(source,script)
    name='run_csharp';args={'path':str(script)}
result=subprocess.run([str(Path(engine)/'bin/managed/sbox-cli.exe'),'--connect',str(settings['pid']),'--request-timeout','45','--call',name,json.dumps(args)],capture_output=True,text=True,encoding='utf-8')
if result.stdout.strip():print(result.stdout)
if result.stderr.strip():print(result.stderr,file=sys.stderr)
sys.exit(result.returncode)
