"""Sequential native editor calls; C# scripts use the connection exchange directory."""
from pathlib import Path
import json, os, subprocess, sys, time, winreg

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/riverdale/cctv-v2'
OUT.mkdir(parents=True, exist_ok=True)
engine = os.environ.get('FACEPUNCH_ENGINE')
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
CLI = Path(engine) / 'bin/managed/sbox-cli.exe'

def call(name, args):
    p = subprocess.run([str(CLI), '--call', name, json.dumps(args)], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    (OUT / f'{time.time_ns()}-{name}.json').write_text(p.stdout + p.stderr, encoding='utf-8')
    if p.returncode:
        raise RuntimeError(p.stdout + p.stderr)
    try: return json.loads(p.stdout)
    except json.JSONDecodeError: return p.stdout.strip()

def rpc(name, args=None, source=None):
    p = subprocess.Popen([str(CLI), '--connect'], cwd=ROOT, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                         encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
    number = 0
    def request(method, params):
        nonlocal number
        number += 1
        p.stdin.write(json.dumps(dict(jsonrpc='2.0', id=number, method=method, params=params)) + '\n')
        p.stdin.flush()
        while True:
            line = p.stdout.readline()
            if not line: raise RuntimeError('Connection ended')
            result = json.loads(line)
            if result.get('id') == number:
                if 'error' in result: raise RuntimeError(result['error'])
                return result['result']
    try:
        initial = request('initialize', dict(protocolVersion='2025-11-25', capabilities={},
                          clientInfo=dict(name='riverdale-cctv', version='1')))
        p.stdin.write(json.dumps(dict(jsonrpc='2.0', method='notifications/initialized')) + '\n')
        p.stdin.flush()
        if source:
            target = Path(initial['_meta']['exchangeDirectory']) / Path(source).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(source).read_bytes())
            args = dict(path=str(target))
        result = request('tools/call', dict(name=name, arguments=args or {}))
        (OUT / f'{time.time_ns()}-script.json').write_text(json.dumps(result, indent=2))
        return result
    finally:
        p.stdin.close()
        p.wait(timeout=15)

def script(source):
    return rpc('run_csharp', source=source)

def large_call(name, args):
    result = rpc(name, args)
    if result.get('isError'): raise RuntimeError(result)
    if 'structuredContent' in result: return result['structuredContent']
    text = '\n'.join(c['text'] for c in result.get('content', []) if c['type']=='text')
    try: return json.loads(text)
    except json.JSONDecodeError: return text

if __name__ == '__main__':
    if sys.argv[1] == 'schema':
        for name in sys.argv[2:]:
            result = call('search_tools', dict(query=name))
            print(json.dumps([t for t in result['tools'] if t['name'] == name], indent=2))
    elif sys.argv[1] == 'script':
        print(json.dumps(script(sys.argv[2]), indent=2))
    else:
        args = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
        print(json.dumps(call(sys.argv[1], args), indent=2))
