"""Shoots Spillway's cargo yard props in s&box, to choose one to rebuild: python candidates.py [shot names]. Nothing is saved or changed.

map_kit's plan (e, n, z) is engine (n, -e, z). The props are placed in Tools/spillway_map.py's cargo_yard().
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/spillway-cargo/candidates"
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-cargo")


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


def shot(name, eye, target, fov=60):
    return f'("{name}", {P(*eye)}, {P(*target)}, {fov}f)'


SHOTS = {
    "yard": shot("yard", (60, -1330, 190), (60, -720, 30), 70),
    "pallet": shot("pallet", (-160, -830, 62), (-195, -688, 4), 55),
    "hose": shot("hose", (130, -950, 70), (90, -1080, 4), 55),
    "cabinets": shot("cabinets", (-250, 190, 64), (-302, 345, 40), 60),
    "case": shot("case", (-240, -260, 66), (-280, -400, 35), 60),
    "case_stack": shot("case_stack", (190, -900, 80), (225, -770, 40), 60),
    "container": shot("container", (-60, -830, 80), (-170, -590, 56), 62),
    # The rest of the map, for the next one (west_works, east_works).
    "turbine_tanks": shot("turbine_tanks", (-1650, 560, 110), (-2200, 700, 90), 62),
    "pump_tanks": shot("pump_tanks", (1900, 1310, 90), (2260, 1310, 80), 72),
    "canvas_cover": shot("canvas_cover", (1560, -1470, 200), (1550, -1705, 165), 60),
    "container_03": shot("container_03", (-1240, -1330, 80), (-1380, -1560, 60), 62),
    "jersey": shot("jersey", (-960, 770, 62), (-1100, 840, 20), 60),
    "wall_unit": shot("wall_unit", (-1170, 300, 70), (-1320, 220, 70), 60),
    "case_stack_east": shot("case_stack_east", (1180, 520, 80), (1300, 650, 40), 60),
}

names = sys.argv[1:] or list(SHOTS)
template = open(os.path.join(HERE, "candidates.cs.txt"), encoding="utf-8").read()
code = template.replace("%OUT%", OUT).replace("%SHOTS%", ", ".join(SHOTS[n] for n in names))
os.makedirs(SCRATCH, exist_ok=True)
path = os.path.join(SCRATCH, "candidates_run.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
started = time.time()
print(call("run_csharp", {"path": path}, 175)[:900].strip(), f"{time.time() - started:.0f}s", flush=True)
