"""Small argv-safe wrapper around this installation's native sbox-cli."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import winreg

parser = argparse.ArgumentParser()
parser.add_argument("tool")
parser.add_argument("values", nargs="*")
parser.add_argument("--args", type=Path)
parser.add_argument("--pick")
parser.add_argument("--save", type=Path)
options = parser.parse_args()
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
arguments = json.loads(options.args.read_text(encoding="utf-8")) if options.args else {}
for item in options.values:
    key, value = item.split("=", 1)
    try:
        arguments[key] = json.loads(value)
    except json.JSONDecodeError:
        arguments[key] = value
result = subprocess.run([str(Path(engine) / "bin/managed/sbox-cli.exe"), "--call", options.tool,
                         json.dumps(arguments)], capture_output=True, text=True)
if options.save:
    options.save.write_text(result.stdout, encoding="utf-8")
    print(json.dumps({"exit_code": result.returncode, "result": str(options.save), "output_characters": len(result.stdout)}))
elif options.pick and result.returncode == 0:
    data = json.loads(result.stdout)
    names = set(options.pick.split(","))
    print(json.dumps([{k: v for k, v in tool.items() if k in ("name", "description", "inputSchema")}
                      for tool in data["tools"] if tool["name"] in names], indent=2))
else:
    print(result.stdout, end="")
if result.stderr:
    print(result.stderr, file=sys.stderr, end="")
sys.exit(result.returncode)
