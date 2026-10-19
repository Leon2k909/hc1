import json
import subprocess
import sys
from pathlib import Path

project = Path(__file__).resolve().parents[3]
cli = Path(r"D:\SteamLibrary\steamapps\common\sbox\bin\managed\sbox-cli.exe")
script = project / "Sources/CerroBlanco/editor/apply-hedge-fill.cs.txt"
raise SystemExit(subprocess.call([str(cli), "--call", "run_csharp", json.dumps({"path": str(script)})], cwd=project))
