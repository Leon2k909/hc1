"""Pass an existing task C# script to the connected editor without shell JSON quoting."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import winreg

source = Path(sys.argv[1]).resolve()
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
cli = str(Path(engine) / "bin/managed/sbox-cli.exe")
status = json.loads(subprocess.check_output([cli, "--call", "instance_status"], text=True))
print(f"Attached to editor PID {status['Pid']}", flush=True)
# Material-only scripts use built-in engine types and carry their own source
# hash guards. They need not wait for unrelated project-code compilation.
if "--asset-only" not in sys.argv[2:]:
    editor = json.loads(subprocess.check_output([cli, "--call", "editor_status"], text=True))
    if editor.get("IsCompiling"):
        raise SystemExit("Editor is compiling; no script dispatched")
exchange = Path(status["ExchangeDirectory"])
exchange.mkdir(parents=True, exist_ok=True)
destination = exchange / source.name
if source != destination:
    shutil.copyfile(source, destination)
print(f"Dispatching {source.name} from the current exchange directory", flush=True)
raise SystemExit(subprocess.call([
    cli, "--connect", str(status['Pid']), "--call", "run_csharp",
    json.dumps({"path": str(destination)}),
]))
