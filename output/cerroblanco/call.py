"""python output/cerroblanco/call.py <script.cs.txt> : runs it in the editor with run_csharp."""
import json, subprocess, sys
from pathlib import Path
cli = r"D:\SteamLibrary\steamapps\common\sbox\bin\managed\sbox-cli.exe"
script = str(Path(sys.argv[1]).resolve())
args = [cli, "--call", "run_csharp", json.dumps({"path": script})]
raise SystemExit(subprocess.call(args, cwd=Path(__file__).resolve().parents[2]))
