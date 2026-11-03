"""Sequential native MCP calls for the Ares interior implementation."""
from pathlib import Path
import json, os, subprocess, sys, time, winreg
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/railhead/pa-speaker-v2'
OUT.mkdir(parents=True,exist_ok=True)
engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as key:
        engine=winreg.QueryValueEx(key,'FACEPUNCH_ENGINE')[0]
CLI=Path(engine)/'bin/managed/sbox-cli.exe'

def target_args():
    wanted=str(ROOT/'hc1.sbproj').replace('\\','/').casefold()
    for attempt in range(3):
        p=subprocess.run([str(CLI),'--list'],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        entries=json.loads(p.stdout)
        matches=[x for x in entries if x.get('kind')=='editor' and str(x.get('project','')).replace('\\','/').casefold()==wanted]
        if matches:break
        time.sleep(.2)
    if len(matches)!=1:raise RuntimeError('Expected one matching native editor: '+str(matches))
    return ['--connect',str(matches[0]['pid'])]

def call(name,args=None):
    p=subprocess.run([str(CLI),*target_args(),'--call',name,json.dumps(args or {})],cwd=ROOT,capture_output=True,
        text=True,encoding='utf-8',timeout=180)
    (OUT/f'{time.time_ns()}-{name}.json').write_text(p.stdout+p.stderr,encoding='utf-8')
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    try:return json.loads(p.stdout)
    except json.JSONDecodeError:return p.stdout.strip()

def script(source):
    p=subprocess.Popen([str(CLI),*target_args()],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
    number=0
    def request(method,params):
        nonlocal number
        number+=1
        p.stdin.write(json.dumps(dict(jsonrpc='2.0',id=number,method=method,params=params))+'\n');p.stdin.flush()
        while True:
            line=p.stdout.readline()
            if not line:raise RuntimeError('Native connection ended')
            result=json.loads(line)
            if result.get('id')==number:
                if 'error' in result:raise RuntimeError(result['error'])
                return result['result']
    try:
        initial=request('initialize',dict(protocolVersion='2025-11-25',capabilities={},clientInfo=dict(name='railhead-pa-speaker',version='1')))
        p.stdin.write(json.dumps(dict(jsonrpc='2.0',method='notifications/initialized'))+'\n');p.stdin.flush()
        target=Path(initial['_meta']['exchangeDirectory'])/Path(source).name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(Path(source).read_bytes())
        result=request('tools/call',dict(name='run_csharp',arguments=dict(path=str(target))))
        (OUT/f'{time.time_ns()}-script.json').write_text(json.dumps(result,indent=2))
        if result.get('isError'):raise RuntimeError(result)
        text='\n'.join(c['text'] for c in result.get('content',[]) if c['type']=='text')
        try:return json.loads(text)
        except json.JSONDecodeError:return text
    finally:
        p.stdin.close();p.wait(timeout=15)

if __name__=='__main__':
    if sys.argv[1]=='schema':
        for name in sys.argv[2:]:
            result=call('search_tools',dict(query=name))
            print(json.dumps([x for x in result['tools'] if x['name']==name],indent=2))
    elif sys.argv[1]=='script':print(json.dumps(script(sys.argv[2]),indent=2))
    else:
        args=json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else {}
        print(json.dumps(call(sys.argv[1],args),indent=2))
