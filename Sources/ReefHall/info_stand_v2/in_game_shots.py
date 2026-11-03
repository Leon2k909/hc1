"""Before and after in a real match, with the HUD and gun: python -X utf8 in_game_shots.py <project root> <reefhall|lowtide> [view name ...]

Needs a match running on that map. For each view: writes view.json, stands the player there with match_view.cs.txt, and takes a screenshot through sbox-cli, the way
Sources/Boxyard/traffic_cone_v2's in-match shots were made. The old bench and bollards are spawned for their "before" shots only, and nothing is saved.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT, MAP = sys.argv[1], sys.argv[2]
WANTED = set(sys.argv[3:])
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
FOLDER = os.path.join(ROOT, "output/asset-improvement-20261030/in-game")
OUT = os.path.join(FOLDER, MAP)
os.makedirs(OUT, exist_ok=True)
SCRIPT = os.path.join(ROOT, "Sources", "ReefHall", "info_stand_v2", "match_view.cs.txt")
STAND = "models/maps/reefhall/info_stand_v2/info_stand.vmdl"
BENCH = "models/maps/reefhall/bench_v2/bench.vmdl"
OLD_BENCH = "models/compare_old/old_reef_bench.vmdl"
BOLLARD = "models/maps/lowtide/mooring_bollard_v2/mooring_bollard.vmdl"
OLD_BOLLARD = "models/compare_old/old_bollard.vmdl"


def world(e, n, z):
    # Plan (e, n, z) is engine (n, -e, z).
    return [n, -e, z]


def frame_of(centre, yaw):
    d = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
    f = (-d[1], d[0])
    return lambda u, w, z: world(centre[0] + d[0] * u + f[0] * w, centre[1] + d[1] * u + f[1] * w, z)


def polar(a, r):
    t = math.radians(a)
    return (r * math.cos(t), r * math.sin(t))


views = []
if MAP == "reefhall":
    # The installed stands, where the map's code puts them, each kept left of the gun.
    for name, centre, yaw in (("stand_rotunda_west", polar(250, 360), 340.0), ("stand_rotunda_east", polar(290, 360), 20.0), ("stand_tunnel", (-400.0, -1180.0), 180.0)):
        at = frame_of(centre, yaw)
        views += [
            dict(name=name, eye=at(34, 84, 0), target=at(-16, 0, 24), extras=[]),
            dict(name=name + "_back", eye=at(30, -92, 0), target=at(16, 0, 26), extras=[]),
        ]
    at = frame_of(polar(250, 360), 340.0)
    views.append(dict(name="stand_far", eye=at(470, 170, 0), target=at(-30, 0, 25), extras=[]))
    # The rotunda's bench. "Before" is the old bench where the old one stood, in the plinth.
    centre, old_centre, yaw = (-215.565, 362.899, 0), (-177.5, 380.65, 0), -155.0
    x, y = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw))), (-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)))
    # Along its length, so the whole bench and the plinth at its end fit beside the gun.
    feet = [centre[0] + x[0] * 120 + y[0] * 66, centre[1] + x[1] * 120 + y[1] * 66, 0]
    aim = [centre[0] - x[0] * 62 + y[0] * 20, centre[1] - x[1] * 62 + y[1] * 20, 12]
    views += [
        dict(name="bench_rotunda_before", eye=feet, target=aim, extras=[dict(model=OLD_BENCH, at=list(old_centre), yaw=yaw)], hide=[BENCH]),
        dict(name="bench_rotunda_after", eye=feet, target=aim, extras=[]),
    ]
    # A gallery's, in brighter light, in the same place before and after.
    spot, yaw = (-92.0, 1480.0, 208.0), -90.0
    feet, aim = [30.0, 1500.0, 208.0], [-92.0, 1512.0, 216.0]
    views += [
        dict(name="bench_gallery_before", eye=feet, target=aim, extras=[dict(model=OLD_BENCH, at=list(spot), yaw=yaw)], hide=[BENCH]),
        dict(name="bench_gallery_after", eye=feet, target=aim, extras=[]),
    ]
else:
    # "Before" is the whole row of old bollards where they stood, the two by the crane legs included.
    old_row = [dict(model=OLD_BOLLARD, at=[-1580.0, -s * e, 0.0], yaw=0.0) for s in (1, -1) for e in range(360, 2200, 330)]
    for name, feet, aim in (
        ("bollard_open", [-1488.0, -1046.0, 0.0], [-1580.0, -990.0, 14.0]),
        ("bollard_crane", [-1578.0, -610.0, 0.0], [-1602.0, -690.0, 14.0]),
        ("bollard_row", [-1512.0, -1420.0, 0.0], [-1580.0, -900.0, 8.0]),
    ):
        views += [
            dict(name=name + "_before", eye=feet, target=aim, extras=old_row, hide=[BOLLARD]),
            dict(name=name + "_after", eye=feet, target=aim, extras=[]),
        ]


def call(tool, payload, timeout=120):
    return subprocess.run([CLI, "--call", tool, json.dumps(payload)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


for view in views:
    if WANTED and view["name"] not in WANTED:
        continue
    with open(os.path.join(FOLDER, "view.json"), "w", encoding="utf-8") as h:
        json.dump(view, h, indent=1)
    placed = call("run_csharp", {"path": SCRIPT})
    reply = placed.stdout.strip()
    print(view["name"], " ".join(reply.split())[:300], placed.stderr[-200:], flush=True)
    # sbox-cli prints the path of the picture it saved, in its own temp folder.
    shot = call("take_screenshot", {})
    path = shot.stdout.strip().splitlines()[-1].strip() if shot.stdout.strip() else ""
    time.sleep(1.0)
    if os.path.exists(path):
        shutil.copyfile(path, os.path.join(OUT, view["name"] + ".png"))
        print("  saved", view["name"], flush=True)
    else:
        print("  no screenshot:", shot.stdout.strip()[:400], shot.stderr[-200:], flush=True)
