"""Own a temporary editor connection until stop-editor.json is written; never attach to another project."""
from pathlib import Path
import json,os,queue,subprocess,sys,threading,time,winreg
ROOT=Path.cwd();OUT=ROOT/'output/orion-generator-installed-20261030';OUT.mkdir(parents=True,exist_ok=True)
engine=os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment') as k:engine=winreg.QueryValueEx(k,'FACEPUNCH_ENGINE')[0]
cli=Path(engine)/'bin/managed/sbox-cli.exe';stop=OUT/'stop-editor.json';assert not stop.exists(),'Stale stop request'
child=subprocess.Popen([str(cli),'--project',str(ROOT/'hc1.sbproj'),'--startup-timeout','600','--idle-timeout','1800'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',bufsize=1,creationflags=subprocess.CREATE_NO_WINDOW)
messages=queue.Queue()
def drain(stream,path,protocol=False):
    with path.open('w',encoding='utf-8') as log:
        for line in stream:
            log.write(line);log.flush()
            if protocol:
                try:messages.put(json.loads(line))
                except json.JSONDecodeError:pass
for stream,name,protocol in [(child.stdout,'editor-protocol.jsonl',True),(child.stderr,'editor-owner.log',False)]:threading.Thread(target=drain,args=(stream,OUT/name,protocol),daemon=True).start()
def send(message):child.stdin.write(json.dumps(message)+'\n');child.stdin.flush()
try:
    send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'approved-orion-generator-import','version':'1'}}})
    deadline=time.monotonic()+620;ready=None
    while time.monotonic()<deadline:
        if child.poll() is not None:raise RuntimeError('Editor owner exited during startup')
        try:message=messages.get(timeout=1)
        except queue.Empty:continue
        if message.get('id')==1:
            if 'error' in message:raise RuntimeError(message)
            ready=message['result'];break
    assert ready is not None,'Editor startup timed out'
    send({'jsonrpc':'2.0','method':'notifications/initialized'});send({'jsonrpc':'2.0','id':2,'method':'tools/list'})
    (OUT/'editor-ready.json').write_text(json.dumps(ready,indent=2));print(json.dumps({'EditorReady':True,'OwnerCliPID':child.pid,'Metadata':ready.get('_meta')}),flush=True)
    deadline=time.monotonic()+1500
    while not stop.exists() and time.monotonic()<deadline:
        if child.poll() is not None:raise RuntimeError('Editor owner exited unexpectedly')
        time.sleep(.5)
finally:
    if child.stdin and not child.stdin.closed:child.stdin.close()
    try:child.wait(timeout=30)
    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=15)
    print(json.dumps({'OwnerCliClosed':True,'ExitCode':child.returncode}),flush=True)
