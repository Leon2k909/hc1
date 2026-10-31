"""Attach to the existing editor, exchange one C# script, and record its result."""
from pathlib import Path
import json,os,shutil,subprocess,sys,winreg
ROOT=Path.cwd();OUT=ROOT/'output/orion-generator-installed-20261030';HERE=ROOT/'Sources/Orion/generator-trial-v1'
engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as k:engine=winreg.QueryValueEx(k,'FACEPUNCH_ENGINE')[0]
cli=Path(engine)/'bin/managed/sbox-cli.exe'
def call(args):return subprocess.run([str(cli),'--call','run_csharp',json.dumps(args)],cwd=ROOT,capture_output=True,text=True)
step=sys.argv[1]
if step=='compile_resources':(OUT/'compile-request.json').write_text(json.dumps({'paths':sys.argv[2:]}))
source=HERE/(step+'.cs.txt');assert source.exists(),source
exchange=call({'code':'return exchangeDirectory;'})
assert exchange.returncode==0,exchange.stderr
directory=Path(exchange.stdout.strip());assert directory.is_absolute() and directory.parent.name=='sbox-cli',directory
directory.mkdir(parents=True,exist_ok=True);target=directory/('orion-generator-'+step+'.cs');shutil.copy2(source,target)
result=call({'path':str(target)});print(result.stdout)
if result.stderr:print(result.stderr,file=sys.stderr)
(OUT/(step+'-last-result.txt')).write_text(result.stdout+result.stderr)
sys.exit(result.returncode)
