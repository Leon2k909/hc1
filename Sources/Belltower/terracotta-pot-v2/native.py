"""Small sbox-cli runner; all scripts copied to its exchange directory."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,winreg
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(tempfile.gettempdir())/'belltower-terracotta-pot-v2'
engine=os.getenv('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
CLI=str(Path(engine)/'bin/managed/sbox-cli.exe')
def call(tool,args=None,name=None):
    p=subprocess.run([CLI,'--call',tool,json.dumps(args or {})],cwd=ROOT,capture_output=True,text=True)
    if name:(OUT/(name+'.json')).write_text(p.stdout if p.returncode==0 else json.dumps({'error':p.stderr,'stdout':p.stdout}))
    if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    try:return json.loads(p.stdout)
    except json.JSONDecodeError:return p.stdout.strip()
def script(path,name):
    exchange=Path(call('run_csharp',{'code':'return exchangeDirectory;'}))
    exchange.mkdir(parents=True,exist_ok=True)
    destination=exchange/Path(path).name
    destination.write_text(Path(path).read_text())
    return call('run_csharp',{'path':str(destination)},name)
if __name__=='__main__':
    if sys.argv[1]=='script':result=script(ROOT/sys.argv[2],sys.argv[3])
    else:result=call(sys.argv[1],json.loads(sys.argv[2]) if len(sys.argv)>2 else {},sys.argv[3] if len(sys.argv)>3 else None)
    print(json.dumps(result,indent=2))
