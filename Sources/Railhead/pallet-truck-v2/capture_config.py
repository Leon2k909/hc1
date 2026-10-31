"""Writes the side-by-side shots' config and script: python capture_config.py <folder name under the work folder>

The new truck stands beside the old one in the goods yard, in a hidden copy of Railhead's scene. Reuses the boulders' capture script, which spawns models beside what's there.
Plan (e, n) is engine (n, -e), and a truck facing +n has its forks along engine +X.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030", "pallet-truck")
folder = sys.argv[1]
ox, oy = -2290.0, -1935.0
# Beside the old one, on the side away from the pallets, which looking along the forks from behind is to its right.
nx, ny = ox, oy - 42.0
mx, my = ox + 18.0, oy - 21.0
stones = [dict(model="models/props/railhead/pallet_truck_v2/truck.vmdl", at=[nx, ny, 0.0], yaw=0.0, scale=1.0)]
views = [
    dict(name="pair", eye=[mx - 96.0, my - 16.0, 64.0], target=[mx + 8.0, my, 10.0], fov=60.0),
    dict(name="pair_side", eye=[mx + 130.0, my - 12.0, 44.0], target=[mx, my, 14.0], fov=50.0),
    dict(name="new_rear", eye=[nx - 62.0, ny - 26.0, 42.0], target=[nx - 4.0, ny, 16.0], fov=50.0),
    dict(name="old_rear", eye=[ox - 62.0, oy - 26.0, 42.0], target=[ox - 4.0, oy, 16.0], fov=50.0),
    dict(name="new_pump", eye=[nx - 34.0, ny - 22.0, 26.0], target=[nx - 4.0, ny, 8.0], fov=50.0),
    dict(name="new_handle", eye=[nx - 34.0, ny - 16.0, 56.0], target=[nx - 9.0, ny, 44.0], fov=50.0),
    dict(name="new_forks", eye=[nx + 66.0, ny - 34.0, 34.0], target=[nx + 26.0, ny, 2.0], fov=50.0),
]
config = dict(
    out=os.path.relpath(os.path.join(WORK, folder), ROOT).replace("\\", "/"),
    scene="Assets/scenes/maps/Railhead/railhead.scene",
    roots=["Sun", "Sky", "Fog", "Look", "Station", "Trees", "Lights", "Reflection Probes", "Station Indirect Light"],
    exposure=1.9, width=1100, height=720, stone_texels=2048, stones=stones, views=views,
)
path = os.path.join(WORK, "capture_config.json")
json.dump(config, open(path, "w"), indent=1)
template = open(os.path.join(ROOT, "Sources", "CerroBlanco", "boulder-v2", "capture_engine.cs.txt"), encoding="utf-8").read()
script = os.path.join(WORK, "capture_engine.cs.txt")
with open(script, "w", encoding="utf-8") as h:
    h.write(template.replace("__CONFIG__", path))
print(script)
