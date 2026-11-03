"""Brighten Spillway's dark interiors: stronger ceiling/wall lights plus shadowless fills.

python Tools/spillway_interior_light.py

Edits Assets/scenes/maps/spillway/spillway.scene in place (run once; re-running is a no-op).
Plan coords are (east, north, up); scene position = (north, -east, up).
"""
import json
import uuid
from pathlib import Path

SCENE = Path(__file__).resolve().parents[1] / "Assets/scenes/maps/spillway/spillway.scene"
NS = uuid.UUID("93bdfe49-6e09-4daa-bba9-8d142274bf3e")
CEILING = ("Turbine interior", "Pumps interior", "A1 lower", "Control upper")
WALL = ("Turbine east", "Red shelter", "B2 shelter", "Stair core entrance")
# name, plan (east, north, up), radius, colour
FILLS = (
    ("Turbine fill west", (-2150, 690, 330), 640, (0.62, 0.66, 0.70)),
    ("Turbine fill east", (-1500, 690, 330), 640, (0.62, 0.66, 0.70)),
    ("Tower fill low", (2045, 300, 200), 560, (0.60, 0.62, 0.64)),
    ("Tower fill high", (2045, 300, 560), 560, (0.45, 0.47, 0.50)),
    ("Pumps fill", (1820, 1320, 260), 520, (0.60, 0.63, 0.66)),
    ("Red shelter fill", (-2110, -1270, 170), 480, (0.62, 0.58, 0.52)),
    ("B2 shelter fill", (2110, -1360, 290), 480, (0.62, 0.58, 0.52)),
    ("Control lower fill", (130, 1060, 120), 420, (0.55, 0.58, 0.62)),
)


def scale(colour, k):
    r, g, b, a = (float(c) for c in colour.split(","))
    return f"{r * k:g},{g * k:g},{b * k:g},{a:g}"


scene = json.loads(SCENE.read_text())
lights = next(o for o in scene["GameObjects"] if o.get("Name") == "Lights")
if any(o["Name"] == FILLS[0][0] for o in lights["Children"]):
    raise SystemExit("already applied")
template = None
for o in lights["Children"]:
    light = o["Components"][0]
    if o["Name"].startswith(CEILING):
        light["LightColor"] = scale(light["LightColor"], 2.2)
        light["Radius"] = round(light["Radius"] * 1.35)
        template = template or o
    elif o["Name"].startswith(WALL):
        light["LightColor"] = scale(light["LightColor"], 1.7)
        light["Radius"] = round(light["Radius"] * 1.3)
for name, (e, n, z), radius, colour in FILLS:
    o = json.loads(json.dumps(template))
    o["__guid"] = str(uuid.uuid5(NS, "light/" + name))
    o["Components"][0]["__guid"] = str(uuid.uuid5(NS, "light-component/" + name))
    o["Name"] = name
    o["Position"] = f"{n},{-e},{z}"
    o["Components"][0].update(Radius=radius, Shadows=False, LightColor="%g,%g,%g,1" % colour)
    lights["Children"].append(o)
SCENE.write_text(json.dumps(scene, indent=2) + "\n")
print("interiors brightened;", len(FILLS), "fills added")
