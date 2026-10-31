"""Write capture_installed.cs.txt's config for one map, from what its scene file really holds: python check_config.py <project root> <boxyard|orion>

Finds each placed prop by its model and aims a view and rays at it, using its own position, turn and scale. A ray that starts outside a prop's collision box and aims at its middle should stop at that box's face,
so "expect" is the distance to the face the map's script gave it. The boxes are the old props' and the scripts didn't change them.
"""
import json
import math
import os
import sys

ROOT, MAP = sys.argv[1], sys.argv[2]
FOLDER = os.path.join(ROOT, "output/asset-improvement-20261030/installed-check")
os.makedirs(FOLDER, exist_ok=True)

# model path part: ( half across the model's x, half along its y, the box's height, the box's centre along y )
BOXES = {
    "ibc_tote": (19.7, 23.6, 45.8, 0.0),
    "wheelie_bin": (12.0, 16.25, 42.2, -0.25),
    "red_crate": (17.0, 22.0, 40.0, 0.0),
}
SETUP = {
    "boxyard": dict(scene="Assets/scenes/maps/Boxyard/boxyard.scene", visual=["Sun", "Sky", "Fog", "Look", "Boxyard", "Lights", "Reflection Probes"], exposure=1.4),
    "orion": dict(scene="Assets/scenes/maps/Orion/orion.scene", visual=["Sun", "Sky", "Fog", "Look", "Orion", "Lights", "Volumetric Fog", "Steam", "Reflection Probes"], exposure=1.1),
}[MAP]


def walk(items):
    for item in items:
        yield item
        yield from walk(item.get("Children", []))


def yaw_of(text):
    x, y, z, w = map(float, text.split(","))
    return math.degrees(2 * math.atan2(z, w))


def turned(at, yaw, x, y, z):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return [at[0] + c * x - s * y, at[1] + s * x + c * y, at[2] + z]


scene = json.load(open(os.path.join(ROOT, SETUP["scene"]), encoding="utf-8"))
views, rays, models = [], [], set()
for item in walk(scene["GameObjects"]):
    for component in item.get("Components", []):
        path = component.get("Model")
        path = path.get("Path") if isinstance(path, dict) else path
        if component.get("__type") != "Sandbox.ModelRenderer" or not path:
            continue
        kind = next((k for k in BOXES if k in path), None)
        if kind is None:
            continue
        models.add(path)
        at = list(map(float, item["Position"].split(",")))
        yaw = yaw_of(item["Rotation"])
        sx, sy, sz = map(float, item["Scale"].split(","))
        hx, hy, tall, mid = BOXES[kind]
        hx, hy, tall, mid = hx * sx, hy * sy, tall * sz, mid * sy
        name = f"{kind}_{len([v for v in views if v['name'].startswith(kind)]) + 1}"
        centre = turned(at, yaw, 0, mid, tall / 2)
        # Stand 2.6 boxes off, at a standing player's eye. Each prop's +x and +y faces are its front, so look from there.
        back = max(hx, hy) * 3.4 + 40
        views.append(dict(name=name, eye=turned(at, yaw, back * 0.8, -back * 0.62, 64.0), target=centre, fov=48))
        views.append(dict(name=name + "_close", eye=turned(at, yaw, hx + 36, hy * 0.5 + mid, tall + 14), target=turned(at, yaw, hx * 0.6, mid, tall * 0.62), fov=48))
        off = 60.0
        for label, ox, oy, expect in (("+x", hx + off, mid, off), ("-x", -hx - off, mid, off), ("+y", 0, mid + hy + off, off), ("-y", 0, mid - hy - off, off)):
            rays.append(dict(label=f"{name} {label}", to=centre, expect=expect, **{"from": turned(at, yaw, ox, oy, tall / 2)}))
        # Over the top: a ray 3 in above the box finds nothing of it.
        over = turned(at, yaw, hx + off, mid, tall + 3)
        rays.append(dict(label=f"{name} over the top", to=turned(at, yaw, -hx - off, mid, tall + 3), expect=-1, **{"from": over}))

config = dict(SETUP, out=f"output/asset-improvement-20261030/installed-check/{MAP}", width=1280, height=800, stream_frames=120, settle_frames=8, models=sorted(models), views=views, rays=rays)
json.dump(config, open(os.path.join(FOLDER, "config.json"), "w", encoding="utf-8"), indent=1)
print(MAP, len(views), "views", len(rays), "rays", sorted(models))
