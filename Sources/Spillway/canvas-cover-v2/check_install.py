"""Check the installed canvas cover in s&box: python check_install.py [folder]. Nothing is saved or changed.

Loads Spillway from its scene file as it is now into an isolated editor scene, counts the covers, fires rays at the collision there (the
old cover's box stays; the cloth has none), and shoots it from compare.py's cameras.
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
engine = os.environ.get("FACEPUNCH_ENGINE")
if not engine:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        engine = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
CLI = os.path.join(engine, "bin", "managed", "sbox-cli.exe")
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-canvas")
CAMERAS = {
    "north": ((1600, -1440, 194), (1550, -1705, 168), 55),
    "northeast": ((1800, -1560, 200), (1550, -1705, 160), 55),
    "east_low": ((1770, -1720, 160), (1550, -1705, 170), 60),
    "far": ((1720, -1180, 200), (1550, -1705, 170), 40),
}


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


folder = sys.argv[1] if len(sys.argv) > 1 else "installed"
shots = ", ".join(f'("installed_{cam}", {P(*eye)}, {P(*target)}, {fov}f)' for cam, (eye, target, fov) in CAMERAS.items())
code = open(os.path.join(HERE, "check_install.cs.txt"), encoding="utf-8").read()
code = code.replace("%OUT%", f"output/asset-improvement-20261030/spillway-canvas/{folder}").replace("%SHOTS%", shots)
code = code.replace("%HIDE%", "false").replace("%PLACE%", "")
started = time.time()
process = subprocess.Popen([CLI, "--connect"], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, encoding="utf-8")
exchange = None
request_id = 0


def request(method, params):
    global request_id
    request_id += 1
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}) + "\n")
    process.stdin.flush()
    while True:
        line = process.stdout.readline()
        if not line:
            raise RuntimeError(process.stderr.read())
        response = json.loads(line)
        if response.get("id") == request_id:
            if "error" in response:
                raise RuntimeError(response["error"])
            return response["result"]


try:
    session = request("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                    "clientInfo": {"name": "canvas-install-check", "version": "1"}})
    exchange = session["_meta"]["exchangeDirectory"]
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    process.stdin.flush()
    path = os.path.join(exchange, "check_install.cs")
    with open(path, "w", encoding="utf-8") as h:
        h.write(code)
    result = request("tools/call", {"name": "run_csharp", "arguments": {"path": path}})
    for block in result.get("content", []):
        if block.get("type") == "text":
            print(block["text"], flush=True)
    if result.get("isError"):
        raise RuntimeError("s&box installed-cover check failed")
    with open(os.path.join(SCRATCH, folder, "native-validation.json"), "w", encoding="utf-8") as h:
        json.dump(result, h, indent=2)
finally:
    process.stdin.close()
    process.wait(timeout=20)
    if exchange:
        shutil.rmtree(exchange)
print(f"{time.time() - started:.0f}s", flush=True)
