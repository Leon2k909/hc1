"""Keep a CLI-owned editor attached until Spillway validation is saved and finished."""
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import winreg

root = Path(__file__).resolve().parents[3]
output = root / 'output/spillway/aaa/editor-host'
output.mkdir(parents=True, exist_ok=True)
stop = output/'stop'
assert not stop.exists(), 'Inspect and clear the previous host stop marker before launching.'
engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
messages = queue.Queue()
with (output/'stderr.log').open('w', encoding='utf-8') as errors:
    process = subprocess.Popen([str(Path(engine)/'bin/managed/sbox-cli.exe'), '--project', str(root/'hc1.sbproj'), '--startup-timeout','600','--request-timeout','600','--idle-timeout','3600'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,encoding='utf-8',bufsize=1)
    (output/'host.json').write_text(json.dumps({'host_pid':os.getpid(),'cli_pid':process.pid,'root':str(root),'started':time.time()}))
    def read():
        with (output/'messages.jsonl').open('w',encoding='utf-8') as log:
            for line in process.stdout:
                log.write(line)
                log.flush()
                messages.put(json.loads(line))
        messages.put(None)
    reader = threading.Thread(target=read,daemon=True)
    reader.start()
    def send(value):
        process.stdin.write(json.dumps(value)+'\n')
        process.stdin.flush()
    def response(identity):
        started = time.monotonic()
        last = started
        while time.monotonic()-started < 650:
            if stop.exists():
                raise RuntimeError('Stop requested during editor startup')
            try:
                item = messages.get(timeout=5)
            except queue.Empty:
                if time.monotonic()-last > 30:
                    print(json.dumps({'waiting_for_editor_seconds':round(time.monotonic()-started)}),flush=True)
                    last = time.monotonic()
                continue
            if item is None:
                raise RuntimeError('Editor host connection ended; inspect stderr and engine log.')
            if item.get('id') == identity:
                if 'error' in item:
                    raise RuntimeError(item['error'])
                return item['result']
        raise TimeoutError('Editor startup exceeded its allowed time')
    try:
        send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'spillway-editor-host','version':'1.0'}}})
        initialized = response(1)
        (output/'initialize.json').write_text(json.dumps(initialized,indent=2))
        send({'jsonrpc':'2.0','method':'notifications/initialized'})
        send({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'editor_status','arguments':{}}})
        status = response(2)
        (output/'ready.json').write_text(json.dumps(status,indent=2))
        print(json.dumps({'ready':True,'metadata':initialized.get('_meta'),'status':status}),flush=True)
        while not stop.exists():
            if process.poll() is not None:
                raise RuntimeError('Editor host exited unexpectedly')
            time.sleep(2)
    finally:
        if process.poll() is None:
            process.stdin.close()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)
        reader.join(timeout=2)
        process.stdout.close()
        print(json.dumps({'editor_host_closed':True,'exit':process.returncode}),flush=True)
