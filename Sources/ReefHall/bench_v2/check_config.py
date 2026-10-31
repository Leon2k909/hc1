"""Write capture_installed.cs.txt's config for one map, from what its scene file holds: python -X utf8 check_config.py <project root> <reefhall|lowtide>

Finds each placed bench or bollard in the scene, aims views and collision rays at it, and adds distance shots for watching the LODs. Engine coordinates throughout.
"""
import json
import math
import os
import sys

ROOT, MAP = sys.argv[1], sys.argv[2]
FOLDER = os.path.join(ROOT, "output/asset-improvement-20261030/bench-bollard-check")
os.makedirs(FOLDER, exist_ok=True)
SETUP = {
    "reefhall": dict(scene="Assets/scenes/maps/ReefHall/reefhall.scene", visual=["Ambient", "Fog", "Aquarium", "Lights", "Reflection Probes"], exposure=1.0),
    "lowtide": dict(scene="Assets/scenes/maps/Lowtide/lowtide.scene", visual=["Sun", "Sky", "Fog", "Look", "Lowtide", "Trees", "Lights", "Reflection Probes"], exposure=2.4),
}[MAP]
KIND = {"reefhall": "bench_v2/bench.vmdl", "lowtide": "mooring_bollard_v2/mooring_bollard.vmdl"}[MAP]


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


def ray(label, start, end, expect):
    return {"label": label, "from": start, "to": end, "expect": expect}


scene = json.load(open(os.path.join(ROOT, SETUP["scene"]), encoding="utf-8"))
views, rays, models, placed = [], [], set(), []
for item in walk(scene["GameObjects"]):
    for component in item.get("Components", []):
        path = component.get("Model")
        path = path.get("Path") if isinstance(path, dict) else path
        if component.get("__type") == "Sandbox.ModelRenderer" and path and KIND in path:
            models.add(path)
            placed.append((item["Name"], list(map(float, item["Position"].split(","))), yaw_of(item["Rotation"])))
if not placed:
    raise SystemExit("Nothing placed yet.")

def index_of_gap(k):
    """Which end of the k-th placed bench faces a display case's plinth: the rotunda's two come first in the scene."""
    return {0: -1, 1: 1}.get(k, 0)


if MAP == "reefhall":
    for k, (name, at, yaw) in enumerate(placed):
        slug = name.lower().replace(" ", "_") + f"_{k}"
        # The model's length is +x and its front +y.
        views.append(dict(name=slug, eye=turned(at, yaw, -46, 118, 62), target=turned(at, yaw, 0, 0, 12), fov=50))
        views.append(dict(name=slug + "_close", eye=turned(at, yaw, 62, 44, 34), target=turned(at, yaw, 24, 0, 12), fov=46))
        off = 60.0
        # The back of a bench can be 9 in from a wall, and the rotunda's ends 2 in from a plinth, so these start close enough to have nothing between them and the bench.
        for label, x, y, gap in (("+y", 0, 9, off), ("-y", 0, -9, 6.0), ("+x", 48, 0, 1.5 if index_of_gap(k) == 1 else off), ("-x", -48, 0, 1.5 if index_of_gap(k) == -1 else off)):
            sign_x, sign_y = (x > 0) - (x < 0), (y > 0) - (y < 0)
            rays.append(ray(f"{slug} seat {label}", turned(at, yaw, x + sign_x * gap, y + sign_y * gap, 16.5), turned(at, yaw, 0, 0, 16.5), gap))
        rays.append(ray(f"{slug} leg", turned(at, yaw, 40, 8 + off, 7), turned(at, yaw, 40, 0, 7), off))
        rays.append(ray(f"{slug} under the seat, between the legs", turned(at, yaw, 0, 40, 7), turned(at, yaw, 0, -14, 7), -1))
        rays.append(ray(f"{slug} over the seat", turned(at, yaw, 0, 40, 20), turned(at, yaw, 0, -14, 20), -1))
    # The rotunda's two, against the plinths they used to run into: from in front and from straight above the gap. "bench 1" and "bench 2" by the scene's order.
    for index, toward in ((0, -1), (1, 1)):
        name, at, yaw = placed[index]
        slug = f"rotunda_gap_{index}"
        views.append(dict(name=slug, eye=turned(at, yaw, toward * 78, 74, 44), target=turned(at, yaw, toward * 66, 0, 10), fov=52))
        views.append(dict(name=slug + "_above", eye=turned(at, yaw, toward * 58, 30, 92), target=turned(at, yaw, toward * 52, 0, 8), fov=56))
        for metres in (12, 25, 40):
            views.append(dict(name=f"{slug}_{metres}m", eye=turned(at, yaw, -toward * metres * 39.37, 0, 64), target=turned(at, yaw, 0, 0, 12), fov=50))
        # Where the old bench's end stood, on the back's side of the plinth. Nothing of it should be left: this ray would have stopped on its seat.
        rays.append(ray(f"{slug} where the old bench's end was", turned(at, yaw, toward * 52, -40, 16.5), turned(at, yaw, toward * 52, -5, 16.5), -1))
else:
    for k, (name, at, yaw) in enumerate(placed):
        slug = f"bollard_{'east' if at[1] < 0 else 'west'}_{abs(at[1]):.0f}"
        views.append(dict(name=slug, eye=[at[0] - 62, at[1] + 34, 38], target=[at[0], at[1], 13], fov=46))
        # In from the harbour: it should stop on the south face, 9 in out from the bollard's centre.
        rays.append(ray(f"{slug} from the harbour", [at[0] - 69, at[1], 12.5], [at[0], at[1], 12.5], 60))
        rays.append(ray(f"{slug} from the side", [at[0], at[1] + 69, 12.5], [at[0], at[1], 12.5], 60))
        rays.append(ray(f"{slug} over the top", [at[0] - 69, at[1], 27], [at[0] + 2, at[1], 27], -1))
    for name, at, yaw in placed:
        if abs(abs(at[1]) - 690) < 1:
            side = "east" if at[1] < 0 else "west"
            # Beside the crane leg's bogie, looking along the gap between them, and from the same spot as the earlier shot of the old one.
            step = 1 if at[1] < 0 else -1
            views.append(dict(name=f"crane_gap_{side}", eye=[at[0] + 3, at[1] + step * 58, 22], target=[at[0] + 3, at[1], 12], fov=44))
            views.append(dict(name=f"crane_above_{side}", eye=[at[0] - 8, at[1], 86], target=[at[0] + 6, at[1], 8], fov=52))
            views.append(dict(name=f"crane_front_{side}", eye=[at[0] - 56, at[1], 34], target=[at[0], at[1], 14], fov=48))
    near = min(placed, key=lambda p: abs(p[1][1] - -1020))[1]
    for metres in (12, 25, 40):
        views.append(dict(name=f"row_{metres}m", eye=[near[0] - 40, near[1] - metres * 39.37, 64], target=[near[0], near[1], 14], fov=42))
    views.append(dict(name="quay_wide", eye=[-1720, -1020, 120], target=[-1560, -700, 14], fov=62))

config = dict(SETUP, out=f"output/asset-improvement-20261030/bench-bollard-check/{MAP}", width=1280, height=800, stream_frames=120, settle_frames=8, models=sorted(models), views=views, rays=rays)
json.dump(config, open(os.path.join(FOLDER, "config.json"), "w", encoding="utf-8"), indent=1)
print(MAP, len(placed), "placed,", len(views), "views,", len(rays), "rays", sorted(models))
