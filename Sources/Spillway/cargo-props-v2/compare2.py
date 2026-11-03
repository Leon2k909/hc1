"""Matched before and after shots of the pallet in s&box: python compare2.py [folder] [setup names]. Nothing is saved or changed.

Four setups, shot from the same cameras with the same held exposure:
- place_before: the map as it is, the old slabs against container 02 in its shadow.
- place_after: the old slabs hidden (comparison material on the cargo model's rv_desk slot) and the new pallets where an install puts them.
- sun_before / sun_after: the same two, moved together to open sunlit floor south of it, so the detail can be seen, with the map's own slabs hidden. The old slabs there are
  cut_old.py's copy of the map's own faces and material.
map_kit's plan (e, n, z) is engine (n, -e, z); a plan heading along e is an engine yaw of 90.
"""
import json
import os
import subprocess
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
SCRATCH = os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-cargo")
HEIGHT = 4.75
PALLET = "models/maps/spillway/pallet_v2/pallet.vmdl"
SLABS = "models/compare_old/spillway_slabs.vmdl"
PLACE = (-197.0, -688.0)  # The old slabs' middle.
SUN = (-230.0, -905.0)  # Open floor in the sun, clear of the cases and the grating.
# Where an install puts the pallets, from the slabs' middle: two singles and a stack of two, a few degrees off square.
LAYOUT = [((-61, 0, 0), 92.0), ((-1, -2, 0), 269.0), ((0, -1, HEIGHT), 94.5), ((58, 2, 0), 276.0)]
# Cameras from the middle of whichever spot: all from the south, as the container is north.
CAMERAS = {
    "standing": ((70, -190, 66), (0, 0, 3), 50),
    "close": ((10, -105, 44), (0, 2, 4), 52),
    "low": ((115, -85, 20), (40, 0, 3), 55),
    "above": ((-5, -75, 100), (0, 0, 0), 62),
}


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


def P(e, n, z):
    return f"new Vector3({n}f, {-e}f, {z}f)"


def pallets(centre):
    return [(PALLET, (centre[0] + de, centre[1] + dn, dz), yaw) for (de, dn, dz), yaw in LAYOUT]


def slabs_at(centre):
    # The copy draws in the map's coordinates at the origin, so move it by the spot's offset from the slabs' own place.
    return [(SLABS, (centre[0] - PLACE[0], centre[1] - PLACE[1], 0.0), 0.0)]


SETUPS = {
    "place_before": (PLACE, [], False),
    "place_after": (PLACE, pallets(PLACE), True),
    "sun_before": (SUN, slabs_at(SUN), True),
    "sun_after": (SUN, pallets(SUN), True),
}


def engine_place(path, at, yaw):
    if path == SLABS:
        # An offset in plan: engine x is n, engine y is -e.
        return f'("{path}", new Vector3({at[1]}f, {-at[0]}f, 0f), 0f)'
    return f'("{path}", {P(*at)}, {yaw}f)'


args = sys.argv[1:]
folder = args.pop(0) if args and args[0] not in SETUPS else "matched"
names = args or list(SETUPS)
template = open(os.path.join(HERE, "compare2.cs.txt"), encoding="utf-8").read()
for name in names:
    centre, placed, hide = SETUPS[name]
    shots = []
    for cam, (eye, target, fov) in CAMERAS.items():
        e = (centre[0] + eye[0], centre[1] + eye[1], eye[2])
        t = (centre[0] + target[0], centre[1] + target[1], target[2])
        shots.append(f'("{name}_{cam}", {P(*e)}, {P(*t)}, {fov}f)')
    code = template.replace("%OUT%", f"output/asset-improvement-20261030/spillway-cargo/{folder}")
    code = code.replace("%SHOTS%", ", ".join(shots)).replace("%HIDE%", "true" if hide else "false")
    code = code.replace("%PLACE%", ", ".join(engine_place(*p) for p in placed) or "")
    path = os.path.join(SCRATCH, f"compare2_{name}.cs")
    with open(path, "w", encoding="utf-8") as h:
        h.write(code)
    started = time.time()
    print(name, " ".join(call("run_csharp", {"path": path}, 175).split())[:300], f"{time.time() - started:.0f}s", flush=True)
