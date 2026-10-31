"""Compile the desk and shoot it beside the old ones in s&box: python capture.py [compile] [shot names]. Nothing in the map changes.

map_kit's plan (e, n, z) is engine (n, -e, z). The control room's floor is z 236 and its back wall runs along n 1330.
The old desks stand at e -190, 60, 310 and 500, each 120 wide and centred on n 1275, so the new one fits between two of them.
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/spillway-desk/engine"
SCRATCH = os.environ.get("DESK_SCRATCH", os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-desk"))
FLOOR = 236.0
NEW_E = 185.0
OLD_E = 60.0


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z + FLOOR}f)"


def shot(name, eye, target, fov=70):
    return f'("{name}", {P(*eye)}, {P(*target)}, {fov}f)'


SHOTS = {
    "pair": shot("pair", (NEW_E, 880, 66), (NEW_E, 1275, 40), 62),
    "pair_low": shot("pair_low", (NEW_E - 20, 1030, 62), (NEW_E, 1275, 42), 62),
    "new_front": shot("new_front", (NEW_E + 40, 1130, 62), (NEW_E, 1275, 42), 62),
    "old_front": shot("old_front", (OLD_E + 40, 1130, 62), (OLD_E, 1275, 42), 62),
    "new_side": shot("new_side", (NEW_E + 66, 1188, 58), (NEW_E, 1270, 42), 70),
    "board": shot("board", (NEW_E - 5, 1205, 66), (NEW_E - 5, 1250, 40), 62),
    "board_close": shot("board_close", (NEW_E + 34, 1214, 56), (NEW_E + 14, 1250, 39), 52),
    "desk_left": shot("desk_left", (NEW_E - 38, 1210, 56), (NEW_E - 30, 1262, 30), 60),
    "desk_right": shot("desk_right", (NEW_E + 44, 1210, 56), (NEW_E + 40, 1262, 30), 60),
    "fronts": shot("fronts", (NEW_E, 1160, 34), (NEW_E, 1275, 16), 62),
    "far": shot("far", (NEW_E, 830, 66), (NEW_E, 1275, 40), 30),
    "screens": shot("screens", (NEW_E, 1160, 68), (NEW_E, 1262, 72), 56),
}


def compile_all():
    for rel in ("materials/spillway/control_desk_v2/cd_glow.vmat", "materials/spillway/control_desk_v2/cd_panel.vmat", "materials/spillway/control_desk_v2/cd_body.vmat", "models/props/spillway/control_desk_v2/control_desk.vmdl"):
        started = time.time()
        out = call("asset_compile", {"path": rel}, 170)
        full = os.path.join(ROOT, "Assets", rel.replace("/", os.sep)) + "_c"
        print(("ok " if os.path.exists(full) else "NO ") + f"{time.time() - started:5.1f}s {rel} {out[:200].strip()}", flush=True)


args = sys.argv[1:]
if "compile" in args:
    compile_all()
    args.remove("compile")
names = args or list(SHOTS)
template = open(os.path.join(HERE, "capture_engine.cs.txt"), encoding="utf-8").read()
code = template.replace("%OUT%", OUT).replace("%PLACES%", P(NEW_E, 1275, 0)).replace("%SHOTS%", ", ".join(SHOTS[n] for n in names))
path = os.path.join(SCRATCH, "capture_run.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
started = time.time()
print(call("run_csharp", {"path": path}, 175)[:900].strip(), f"{time.time() - started:.0f}s", flush=True)
