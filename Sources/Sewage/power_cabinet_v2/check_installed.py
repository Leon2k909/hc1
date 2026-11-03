"""Check the installed cabinets in s&box: python check_installed.py [view ...]

Writes engine/config.json and runs check_installed.cs.txt, which reads the real sewage.scene into an isolated editor scene. Views are in the map
generator's plan coordinates (east, north, up); the pictures go in engine/ as <view>-installed.png.
"""
import json
import os
import subprocess
import sys

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(ROOT, "output", "asset-improvement-20261030", "sewage-power-cabinet", "engine")


def world(e, n, z):
    return [n, -e, z]


VIEWS = {
    "hero": ((-790, 395, 64), (-955, 465, 60), 60),
    "a_side": ((-760, 300, 64), (-958, 430, 62), 70),
    "b_wide": ((745, 660, 64), (946, 600, 58), 70),
    "b_side": ((800, 500, 64), (946, 575, 60), 70),
    "c_wide": ((-700, 760, 416), (-870, 830, 410), 75),
    "c_stairs": ((-820, 735, 418), (-870, 795, 415), 75),
}
picked = sys.argv[1:] or list(VIEWS)
config = dict(
    exposure=2.0,
    stream_frames=70,
    settle_frames=14,
    width=1280,
    height=800,
    views=[dict(name=k, eye=world(*VIEWS[k][0]), target=world(*VIEWS[k][1]), fov=VIEWS[k][2]) for k in picked],
)
with open(os.path.join(ENGINE, "config.json"), "w") as h:
    json.dump(config, h, indent=1)
run = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": os.path.join(HERE, "check_installed.cs.txt")})], cwd=ROOT, capture_output=True, timeout=240)
print((run.stdout + run.stderr).decode("utf-8", "replace")[:3500])
