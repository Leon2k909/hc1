"""Writes the installed tyres' shots: python check_config.py <folder name under the work folder>

The stacks as the scene file now has them, on both sides, in a hidden copy of Railhead's scene, with nothing spawned. Reuses the boulders' capture script.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030", "tyre")
views = []
for name, y, side in (("east", -1877.0, -1.0), ("west", 1877.0, 1.0)):
    views.append(dict(name=f"installed_{name}", eye=[-2190.0, y + side * 110.0, 62.0], target=[-2110.0, y, 16.0], fov=60.0))
    views.append(dict(name=f"installed_{name}_close", eye=[-2172.0, y + side * 58.0, 48.0], target=[-2160.0, y, 18.0], fov=50.0))
config = dict(
    out=os.path.relpath(os.path.join(WORK, sys.argv[1]), ROOT).replace("\\", "/"),
    scene="Assets/scenes/maps/Railhead/railhead.scene",
    roots=["Sun", "Sky", "Fog", "Look", "Station", "Trees", "Lights", "Reflection Probes", "Station Indirect Light"],
    exposure=1.9, width=1100, height=720, stone_texels=2048, stones=[], views=views,
)
path = os.path.join(WORK, "check_config.json")
json.dump(config, open(path, "w"), indent=1)
template = open(os.path.join(ROOT, "Sources", "CerroBlanco", "boulder-v2", "capture_engine.cs.txt"), encoding="utf-8").read()
script = os.path.join(WORK, "check_engine.cs.txt")
with open(script, "w", encoding="utf-8") as h:
    h.write(template.replace("__CONFIG__", path))
print(script)
