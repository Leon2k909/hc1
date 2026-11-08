import json, subprocess, sys
args = sys.argv[2:]
payload = open(args[0], encoding='utf-8-sig').read() if args else '{}'
p = subprocess.run(['C:/Program Files (x86)/Steam/steamapps/common/sbox/bin/managed/sbox-cli.exe', '--call', sys.argv[1], payload], capture_output=True, text=True)
print(p.stdout)
print(p.stderr, file=sys.stderr)
sys.exit(p.returncode)
