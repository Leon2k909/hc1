"""Pass an sbox-cli tool call with intact JSON quoting on Windows PowerShell."""
import json
import os
import subprocess
import sys
from pathlib import Path

cli = Path(os.environ['FACEPUNCH_ENGINE']) / 'bin' / 'managed' / 'sbox-cli.exe'
name = sys.argv[1]
arg_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if arg_path and arg_path.suffix == '.cs':
    args = {'code': arg_path.read_text('utf-8')}
else:
    args = json.loads(arg_path.read_text('utf-8')) if arg_path else {}
result = subprocess.run([str(cli), '--connect', '2652', '--call', name, json.dumps(args)], capture_output=True, text=True)
print(result.stdout or result.stderr)
sys.exit(result.returncode)
