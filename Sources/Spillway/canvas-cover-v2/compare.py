"""Matched before and after shots of the canvas cover in s&box: python compare.py [folder] [setup names]. Nothing is saved or changed.

- before: the map as it is.
- after: the east model's sw_tarp and rv_dark slots hidden, cut_old.py's copy of its other rv_dark faces put back, and the new cover
  placed where an install puts it. So the old cover and its straps are gone and everything else stays.
Same cameras and held exposure for both. map_kit's plan (e, n, z) is engine (n, -e, z); the deck is at z 128.
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-canvas")
NEW = "models/maps/spillway/canvas_cover_v2/canvas_cover.vmdl"
REST = "models/compare_old/spillway_east_dark_rest.vmdl"
CENTRE = (1550.0, -1705.0, 128.0)
CAMERAS = {
    "north": ((1600, -1440, 194), (1550, -1705, 168), 55),
    "northeast": ((1800, -1560, 200), (1550, -1705, 160), 55),  # Clear of the lamp mast at e 1630, n -1600.
    "east_low": ((1770, -1720, 160), (1550, -1705, 170), 60),
    "above": ((1560, -1560, 300), (1550, -1705, 190), 62),
    "far": ((1720, -1180, 200), (1550, -1705, 170), 40),
}
SETUPS = {
    "before": ([], []),
    "after": ([(NEW, CENTRE), (REST, (0.0, 0.0, 0.0))], ["sw_tarp", "rv_dark"]),
}


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


args = sys.argv[1:]
folder = args.pop(0) if args and args[0] not in SETUPS else "matched"
names = args or list(SETUPS)
os.makedirs(SCRATCH, exist_ok=True)
template = open(os.path.join(HERE, "compare.cs.txt"), encoding="utf-8").read()
for name in names:
    placed, hide = SETUPS[name]
    shots = ", ".join(f'("{name}_{cam}", {P(*eye)}, {P(*target)}, {fov}f)' for cam, (eye, target, fov) in CAMERAS.items())
    # The cut-out is in the map model's own coordinates, so it goes at the world origin; the cover at its spot, unturned.
    place = ", ".join(f'("{path}", {"new Vector3(0f, 0f, 0f)" if path == REST else P(*at)}, 0f)' for path, at in placed)
    code = template.replace("%OUT%", f"output/asset-improvement-20261030/spillway-canvas/{folder}").replace("%SHOTS%", shots)
    code = code.replace("%PLACE%", place).replace("%HIDE%", "true" if hide else "false").replace("%HIDE_MATS%", ", ".join(f'"{m}"' for m in hide))
    path = os.path.join(SCRATCH, f"compare_{name}.cs")
    with open(path, "w", encoding="utf-8") as h:
        h.write(code)
    started = time.time()
    print(name, " ".join(call("run_csharp", {"path": path}, 175).split())[:300], f"{time.time() - started:.0f}s", flush=True)
