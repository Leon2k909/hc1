import json, subprocess, sys
from pathlib import Path
exe = Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe')
args = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 and Path(sys.argv[2]).exists() else ({'name':sys.argv[2]} if len(sys.argv)>2 else {})
r = subprocess.run([str(exe), '--call', sys.argv[1], json.dumps(args)], capture_output=True, text=True)
print(r.stdout)
print(r.stderr, file=sys.stderr)
sys.exit(r.returncode)
