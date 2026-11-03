"""Check the installed pallets in s&box: python check_install.py [folder]. Nothing is saved or changed.

Loads Spillway from its scene file as it is now into an isolated editor scene, counts the pallets and their colliders, fires rays at them,
and shoots them from compare2.py's cameras over the real spot.
"""
import json
import os
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-cargo")
PLACE = (-197.0, -688.0)
CAMERAS = {
    "standing": ((70, -190, 66), (0, 0, 3), 50),
    "close": ((10, -105, 44), (0, 2, 4), 52),
    "low": ((115, -85, 20), (40, 0, 3), 55),
    "above": ((-5, -75, 100), (0, 0, 0), 62),
}


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


folder = sys.argv[1] if len(sys.argv) > 1 else "installed"
shots = []
for cam, (eye, target, fov) in CAMERAS.items():
    e = (PLACE[0] + eye[0], PLACE[1] + eye[1], eye[2])
    t = (PLACE[0] + target[0], PLACE[1] + target[1], target[2])
    shots.append(f'("installed_{cam}", {P(*e)}, {P(*t)}, {fov}f)')
code = open(os.path.join(HERE, "check_install.cs.txt"), encoding="utf-8").read()
code = code.replace("%OUT%", f"output/asset-improvement-20261030/spillway-cargo/{folder}").replace("%SHOTS%", ", ".join(shots))
code = code.replace("%HIDE%", "false").replace("%PLACE%", "")
path = os.path.join(SCRATCH, "check_install_run.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
started = time.time()
run = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": path})], cwd=ROOT, capture_output=True, timeout=175)
print((run.stdout + run.stderr).decode("utf-8", "replace")[:2500].strip(), f"{time.time() - started:.0f}s", flush=True)
