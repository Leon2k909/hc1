"""Before or after shots in a running Riverdale match: python live_shots.py <project root> <scratch dir> <before|after>

Reads the placements install_extinguishers.py wrote. "after" also stands the new model at each placement for this match. Doesn't move the player's view.
"""
import json
import os
import subprocess
import sys

CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
ROOT, SCRATCH, MODE = sys.argv[1:4]
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "output/asset-improvement-20261030/riverdale-extinguisher")
places = json.load(open(os.path.join(WORK, "placements.json")))


def view(name, place, dist, side, height, fov=55):
    x, y, z = place["at"]
    ox, oy = place["out"]
    # Right as you face the wall.
    rx, ry = oy, -ox
    eye = [x + ox * dist + rx * side, y + oy * dist + ry * side, z + height]
    target = [x, y, z + 21]
    return dict(name=name, eye=eye, target=target, fov=fov)


def find(x, y):
    return min(places, key=lambda p: (p["at"][0] - x) ** 2 + (p["at"][1] - y) ** 2)


views = [
    view("close", find(1621, -640), 46, 8, 24, 50),
    view("deck", find(1090, -1000), 96, 20, 34),
    view("upper", find(1300, -1000), 96, -20, 34),
    view("south-wall", find(-200, -140), 110, 26, 34),
]
config = os.path.join(SCRATCH, "live_shots.json")
json.dump(dict(out=os.path.join(WORK, "shots").replace("\\", "/"), places=places, views=views), open(config, "w"))
text = open(os.path.join(HERE, "live_shots.cs.txt"), encoding="utf-8").read()
text = text.replace("__CONFIG__", config.replace("\\", "/")).replace("__SPAWN__", "true" if MODE == "after" else "false").replace("__WAIT__", "5000" if MODE == "after" else "200").replace("__MODE__", MODE)
script = os.path.join(SCRATCH, "live_shots_run.cs.txt")
open(script, "w", encoding="utf-8", newline="\n").write(text)
r = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": script.replace("\\", "/")})], capture_output=True, text=True, cwd=ROOT, timeout=170, encoding="utf-8", errors="replace")
print(r.returncode, r.stdout.strip()[-900:], r.stderr.strip()[-500:], flush=True)
sys.exit(r.returncode)
