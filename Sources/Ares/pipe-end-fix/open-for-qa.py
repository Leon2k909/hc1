"""Own a temporary native editor connection until QA releases it; always close it."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import winreg

root=Path(__file__).resolve().parents[3]
out=root/'output/ares/pipe-end-fix'
engine=os.environ.get('FACEPUNCH_ENGINE') or winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER,'Environment'),'FACEPUNCH_ENGINE')[0]
release=out/'release-editor'
assert not release.exists(),'Choose a fresh QA session.'
messages=queue.Queue()
with (out/'editor-launch.log').open('w',encoding='utf8') as errors:
    process=subprocess.Popen([str(Path(engine)/'bin/managed/sbox-cli.exe'),'--project',str(root/'hc1.sbproj'),
        '--request-timeout','60'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,
        text=True,encoding='utf8',bufsize=1)
    def read():
        for line in process.stdout:
            try:messages.put(json.loads(line))
            except ValueError:pass
        messages.put(None)
    thread=threading.Thread(target=read,daemon=True);thread.start()
    try:
        process.stdin.write(json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{
            'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'pipe-cap-qa','version':'1'}}})+'\n')
        process.stdin.flush()
        deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            message=messages.get(timeout=max(1,deadline-time.monotonic()))
            if message is None:raise RuntimeError('Editor launch connection exited; inspect editor-launch.log.')
            if message.get('id')==1:
                assert 'result' in message,message
                metadata=message['result'].get('_meta',{})
                (out/'owned-editor.json').write_text(json.dumps(metadata,indent=2))
                print(json.dumps(metadata),flush=True)
                break
        else:raise RuntimeError('Editor launch timed out.')
        process.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');process.stdin.flush()
        deadline=time.monotonic()+1800
        while not release.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.5)
    finally:
        process.stdin.close()
        try:process.wait(timeout=20)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        thread.join(timeout=2);process.stdout.close()
        print(json.dumps({'native_launch_connection_closed':True,'returncode':process.returncode}),flush=True)
