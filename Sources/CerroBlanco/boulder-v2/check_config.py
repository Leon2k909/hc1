"""Writes check_install's config and script: python check_config.py <folder name under the work folder>"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030", "cerroblanco-boulder")
GARDEN = (-1743.0, -1359.0)
SPOTS = ((45, 320, "new"), (140, 300, "new"), (228, 340, "old"), (312, 290, "new"), (70, 400, "new"), (200, 410, "old"))
views, probes = [], []
cx, cy = GARDEN[1], -GARDEN[0]
views.append(dict(name="garden_overview", eye=[cx + 330, cy - 560, 300.0], target=[cx - 40, cy + 40, 0.0], fov=70.0))
for k, (a, r, kind) in enumerate(SPOTS):
    e, n = GARDEN[0] + r * math.cos(math.radians(a)), GARDEN[1] + r * math.sin(math.radians(a))
    x, y = n, -e
    # From the garden's middle side, at a player's eyes, so the path and the sphere's plinth aren't in the way.
    dx, dy = cx - x, cy - y
    length = math.hypot(dx, dy)
    views.append(dict(name=f"stone_{k}_{kind}", eye=[x + dx / length * 118, y + dy / length * 118, 64.0], target=[x, y, 14.0], fov=55.0))
    probes.append(dict(name=f"{k} {kind} middle", at=[x, y, 0.0]))
config = dict(
    out=os.path.relpath(os.path.join(WORK, sys.argv[1]), ROOT).replace("\\", "/"),
    scene="Assets/scenes/maps/CerroBlanco/cerroblanco.scene",
    roots=["Sun", "Sky", "Fog", "Look", "Cerro Blanco", "Trees", "Lights", "Reflection Probes", "Cerro Blanco construction details", "Museum indirect light"],
    exposure=3.0, width=1100, height=720, views=views, probes=probes,
)
path = os.path.join(WORK, "check_config.json")
json.dump(config, open(path, "w"), indent=1)
template = open(os.path.join(HERE, "check_install.cs.txt"), encoding="utf-8").read()
script = os.path.join(WORK, "check_install.cs.txt")
with open(script, "w", encoding="utf-8") as h:
    h.write(template.replace("__CONFIG__", path))
print(script)
