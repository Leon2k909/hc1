"""Bounded startup observer; leaves a successful user-requested editor open."""
from pathlib import Path
import ctypes
import datetime
import json
import os
import subprocess
import time
import winreg

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
engine = Path(engine)
running = subprocess.run(["rtk", "proxy", "tasklist", "/FI", "IMAGENAME eq sbox-dev.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=True)
if '"sbox-dev.exe"' in running.stdout.lower():
    raise SystemExit("An editor already exists; attach instead of duplicating it.")
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
record_path = OUT / f"startup-observation-{stamp}.json"
record = {"project": str(ROOT / "hc1.sbproj"), "engine": str(engine), "started_utc": stamp, "samples": []}
proc = subprocess.Popen([str(engine / "sbox-dev.exe"), "-project", str(ROOT / "hc1.sbproj")], cwd=engine)
record["pid"] = proc.pid
print(json.dumps({"pid": proc.pid, "record": str(record_path)}), flush=True)
started = time.monotonic()
while time.monotonic() - started < 300:
    code = proc.poll()
    log = engine / "logs" / "sbox-dev.log"
    tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-1:] if log.exists() else []
    row = {"elapsed_s": round(time.monotonic() - started, 1), "exit_code": code, "last_log": tail}
    record["samples"].append(row)
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(row), flush=True)
    if code is not None:
        record["exit_hex"] = f"0x{code & 0xffffffff:08X}"
        record["ended_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps({"exit_code": code, "exit_hex": record["exit_hex"]}), flush=True)
        break
    time.sleep(10)
else:
    record["observation_complete_editor_left_open"] = True
    record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
