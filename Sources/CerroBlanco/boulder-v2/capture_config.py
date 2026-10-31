"""Writes the side-by-side shots' config and script: python capture_config.py <folder name under the work folder> <texels to ask for>

Each new stone stands beside an old one on the same lawn. Plan (e, n) is engine (n, -e), and the garden's boulders stand round its middle.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030", "cerroblanco-boulder")
folder = sys.argv[1]
texels = int(sys.argv[2])
GARDEN = (-1743.0, -1359.0)
MODEL = "models/props/cerroblanco/boulder_v2/boulder_{}.vmdl"


def old_at(angle, radius):
    e = GARDEN[0] + radius * math.cos(math.radians(angle))
    n = GARDEN[1] + radius * math.sin(math.radians(angle))
    return n, -e


stones, views = [], []
# The old stone, then the new one to the viewer's right of it, seen from where a player would stand on the path side.
back = (0.809, -0.588)
right = (0.588, 0.809)
for name, angle, radius, shape, yaw, gap in (("a", 45, 320, "a", 30.0, 92.0), ("b", 140, 300, "b", 200.0, 76.0)):
    ox, oy = old_at(angle, radius)
    nx, ny = ox + right[0] * gap, oy + right[1] * gap
    stones.append(dict(model=MODEL.format(shape), at=[nx, ny, 0.0], yaw=yaw, scale=1.0))
    mx, my = (ox + nx) / 2, (oy + ny) / 2
    views.append(dict(name=f"pair_{name}", eye=[mx + back[0] * 170, my + back[1] * 170, 64.0], target=[mx, my, 16.0], fov=60.0))
    views.append(dict(name=f"new_{name}_close", eye=[nx + back[0] * 92, ny + back[1] * 92, 44.0], target=[nx, ny, 16.0], fov=55.0))
    views.append(dict(name=f"old_{name}_close", eye=[ox + back[0] * 92, oy + back[1] * 92, 44.0], target=[ox, oy, 14.0], fov=55.0))
    if name == "a":
        views.append(dict(name="new_a_crouched", eye=[nx + back[0] * 46 - right[0] * 22, ny + back[1] * 46 - right[1] * 22, 34.0], target=[nx, ny, 22.0], fov=60.0))
config = dict(
    out=os.path.relpath(os.path.join(WORK, folder), ROOT).replace("\\", "/"),
    scene="Assets/scenes/maps/CerroBlanco/cerroblanco.scene",
    roots=["Sun", "Sky", "Fog", "Look", "Cerro Blanco", "Trees", "Lights", "Reflection Probes", "Cerro Blanco construction details", "Museum indirect light"],
    exposure=3.0, width=1100, height=720, stone_texels=texels, stones=stones, views=views,
)
path = os.path.join(WORK, "capture_config.json")
json.dump(config, open(path, "w"), indent=1)
template = open(os.path.join(HERE, "capture_engine.cs.txt"), encoding="utf-8").read()
script = os.path.join(WORK, "capture_engine.cs.txt")
with open(script, "w", encoding="utf-8") as h:
    h.write(template.replace("__CONFIG__", path))
print(script)
