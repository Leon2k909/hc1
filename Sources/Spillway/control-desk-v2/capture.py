"""Compile the installed desks and check them in s&box: python capture.py [compile] [shot names]. Nothing is saved or changed.

map_kit's plan (e, n, z) is engine (n, -e, z). The control room's floor is z 236 and its back wall runs along n 1330.
The desks stand at e -190, 60, 310 and 500, each 120 wide and centred on n 1275. compose.py's sheet came from the version of this before the install, with one desk between two old ones.
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/spillway-desk/installed"
SCRATCH = os.environ.get("DESK_SCRATCH", os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-desk"))
FLOOR = 236.0
DESK_E = 60.0


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z + FLOOR}f)"


def shot(name, eye, target, fov=70):
    return f'("{name}", {P(*eye)}, {P(*target)}, {fov}f)'


SHOTS = {
    "room": shot("room", (155, 860, 72), (155, 1275, 52), 76),
    "room_side": shot("room_side", (-340, 1120, 70), (360, 1285, 48), 66),
    "desk_front": shot("desk_front", (DESK_E + 40, 1130, 62), (DESK_E, 1275, 42), 62),
    "desk_side": shot("desk_side", (DESK_E + 66, 1188, 58), (DESK_E, 1270, 42), 70),
    "board": shot("board", (DESK_E - 5, 1205, 66), (DESK_E - 5, 1250, 40), 62),
    "desk_left": shot("desk_left", (DESK_E - 38, 1210, 56), (DESK_E - 30, 1262, 30), 60),
    "fronts": shot("fronts", (DESK_E, 1160, 34), (DESK_E, 1275, 16), 62),
    # Under the top and over the hood: where a wrongly dropped face would show.
    "check_low": shot("check_low", (DESK_E - 8, 1196, 5), (DESK_E, 1275, 30), 80),
    "check_top": shot("check_top", (DESK_E + 30, 1205, 112), (DESK_E, 1290, 60), 70),
    "lod1": shot("lod1", (DESK_E + 40, 1130, 62), (DESK_E, 1275, 42), 62),
    "lod2": shot("lod2", (DESK_E + 40, 1130, 62), (DESK_E, 1275, 42), 62),
}


def compile_all():
    for rel in ("materials/spillway/control_desk_v2/cd_glow.vmat", "materials/spillway/control_desk_v2/cd_panel.vmat", "materials/spillway/control_desk_v2/cd_body.vmat", "models/props/spillway/control_desk_v2/control_desk.vmdl", "models/maps/spillway/spillway_control.vmdl", "scenes/maps/spillway/spillway.scene"):
        started = time.time()
        out = call("asset_compile", {"path": rel}, 170)
        # An old _c alone counts for nothing: the CLI exits cleanly with no editor running. The editor can leave a _c older than its source when the contents haven't changed.
        full = os.path.join(ROOT, "Assets", rel.replace("/", os.sep))
        good = os.path.exists(full + "_c") and '"Success": true' in out
        print(("ok " if good else "NO ") + f"{time.time() - started:5.1f}s {rel} {out[:200].strip()}", flush=True)


args = sys.argv[1:]
if "compile" in args:
    compile_all()
    args.remove("compile")
names = args or list(SHOTS)
template = open(os.path.join(HERE, "capture_engine.cs.txt"), encoding="utf-8").read()
code = template.replace("%OUT%", OUT).replace("%SHOTS%", ", ".join(SHOTS[n] for n in names))
path = os.path.join(SCRATCH, "capture_run.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
started = time.time()
print(call("run_csharp", {"path": path}, 175)[:900].strip(), f"{time.time() - started:.0f}s", flush=True)
