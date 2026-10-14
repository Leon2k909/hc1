"""Pass structured arguments to an attached native CLI without shell quoting."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import winreg

p = argparse.ArgumentParser()
p.add_argument("tool")
p.add_argument("--arguments", type=Path)
p.add_argument("--script", type=Path)
p.add_argument("--output", type=Path)
args = p.parse_args()
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
data = json.loads(args.arguments.read_text()) if args.arguments else {}
if args.script:
    data["path"] = str(args.script.resolve())
result = subprocess.run(["rtk", "proxy", str(Path(engine) / "bin/managed/sbox-cli.exe"),
    "--call", args.tool, json.dumps(data)], capture_output=True, text=True, encoding="utf-8")
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.stdout, encoding="utf-8")
    print(f"{args.tool}: exit={result.returncode}; output={args.output}")
else:
    print(result.stdout, end="")
if result.stderr:
    print(result.stderr, end="", file=sys.stderr)
sys.exit(result.returncode)
