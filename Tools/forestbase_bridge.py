"""Small local client for the project's existing S&box editor file IPC."""
import json, os, time, uuid, argparse
from pathlib import Path

def call(command, params=None, timeout=50):
    folder = Path(os.environ['TEMP']) / 'sbox-bridge-ipc'
    key = str(uuid.uuid4())
    request = folder / f'req_{key}.json'
    temp = request.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(id=key, command=command, params=params or {}, protocolVersion=1)), encoding='utf-8')
    temp.replace(request)
    response = folder / f'res_{key}.json'
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response.exists():
            result = json.loads(response.read_text(encoding='utf-8-sig'))
            response.unlink()
            return result
        time.sleep(.1)
    raise TimeoutError(f'Editor did not answer {command} in {timeout}s; request {key}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command')
    parser.add_argument('params', nargs='?', default='{}')
    args = parser.parse_args()
    print(json.dumps(call(args.command, json.loads(args.params)), indent=2))
