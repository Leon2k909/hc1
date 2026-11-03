"""Small synchronous MCP client; scripts live in the connection's exchange directory and are removed on exit."""
import json
import os
from pathlib import Path
import shutil
import subprocess


class Editor:
    def __enter__(self):
        engine = os.environ.get('FACEPUNCH_ENGINE')
        if not engine:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
                engine = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
        self.root = Path(__file__).absolute().parents[3]
        self.process = subprocess.Popen([str(Path(engine) / 'bin/managed/sbox-cli.exe'), '--connect'], cwd=self.root,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding='utf-8')
        self.counter = 0
        session = self.request('initialize', dict(protocolVersion='2025-11-25', capabilities={},
                                                clientInfo=dict(name='codex-hose-model', version='1')))
        self.exchange = Path(session['_meta']['exchangeDirectory'])
        self.process.stdin.write(json.dumps(dict(jsonrpc='2.0', method='notifications/initialized')) + '\n')
        self.process.stdin.flush()
        return self

    def request(self, method, params):
        self.counter += 1
        self.process.stdin.write(json.dumps(dict(jsonrpc='2.0', id=self.counter, method=method, params=params)) + '\n')
        self.process.stdin.flush()
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError(self.process.stderr.read())
            message = json.loads(line)
            if message.get('id') == self.counter:
                if 'error' in message:
                    raise RuntimeError(message['error'])
                return message['result']

    def call(self, name, arguments=None):
        result = self.request('tools/call', dict(name=name, arguments=arguments or {}))
        blocks = [block['text'] for block in result.get('content', []) if block.get('type') == 'text']
        text = '\n'.join(blocks)
        if result.get('isError'):
            raise RuntimeError(name + ': ' + text)
        try:
            return json.loads(text)
        except ValueError:
            return text

    def script(self, code, name='review.cs'):
        path = self.exchange / name
        path.write_text(code, encoding='utf-8')
        return self.call('run_csharp', dict(path=str(path)))

    def __exit__(self, *unused):
        self.process.stdin.close()
        self.process.wait(timeout=20)
        shutil.rmtree(self.exchange)
