"""Writes the side-by-side shots' config and script: python capture_config.py <folder name under the work folder>

A new stack of four stands beside the old stack of four against the goods shed, in a hidden copy of Railhead's scene. Reuses the boulders' capture script, which spawns models beside what's there.
The old stack is at plan (1876, -2160), which is engine (-2160, -1876), and tyres stack 8.07 apart.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030", "tyre")
folder = sys.argv[1]
ox, oy = -2160.0, -1876.0
nx, ny = ox - 40.0, oy - 2.0
MODEL = "models/props/railhead/tyre_v2/tyre_{}.vmdl"
stones = []
for k, (shape, yaw) in enumerate((("a", 20.0), ("b", 130.0), ("a", 250.0), ("b", 310.0))):
    de, dn = math.sin(k * 2.1) * 1.4, math.cos(k * 1.7) * 1.2
    stones.append(dict(model=MODEL.format(shape), at=[nx + dn, ny - de, 0.3 + k * 8.07], yaw=yaw, scale=1.0))
mx, my = (ox + nx) / 2, (oy + ny) / 2
views = [
    dict(name="pair", eye=[mx - 8.0, my - 98.0, 60.0], target=[mx, my, 16.0], fov=55.0),
    dict(name="pair_low", eye=[mx - 10.0, my - 72.0, 22.0], target=[mx, my, 16.0], fov=60.0),
    dict(name="new_close", eye=[nx - 22.0, ny - 44.0, 42.0], target=[nx, ny, 22.0], fov=50.0),
    dict(name="old_close", eye=[ox + 22.0, oy - 44.0, 42.0], target=[ox, oy, 22.0], fov=50.0),
    dict(name="new_top", eye=[nx - 10.0, ny - 18.0, 64.0], target=[nx, ny, 32.0], fov=55.0),
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
