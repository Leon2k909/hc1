"""Write the engine capture's config, reading each cone's place and turn from the merged props model: python capture_config.py <project root>"""
import json
import math
import os
import sys

import numpy as np

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "output/asset-improvement-20261030/traffic-cone/engine")
os.makedirs(OUT, exist_ok=True)
PROPS = os.path.join(ROOT, "Assets/models/maps/boxyard/boxyard_props.obj")
# boxyard_map's (e, n) are engine (n, -e).
STANDING = [(-166.0, 54.0), (511.0, -688.0), (549.0, -558.0), (563.0, -593.0)]
LYING = (-191.0, 45.0)

positions, plastic, orange = [], [], []
current = None
for line in open(PROPS, encoding="utf-8"):
    if line.startswith("v "):
        a, b, c = map(float, line[2:].split())
        positions.append((c, a, b))
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif line.startswith("f ") and current in ("bx_black_plastic", "bx_cone_orange", "bx_reflective"):
        points = [positions[int(t.split("/")[0]) - 1] for t in line.split()[1:]]
        (plastic if current == "bx_black_plastic" else orange).extend(points)
plastic, orange = np.array(plastic), np.array(orange)

cones = []
for x, y in STANDING:
    near = plastic[np.hypot(plastic[:, 0] - x, plastic[:, 1] - y) < 11.0]
    if len(near) == 0:
        raise SystemExit(f"No old cone at {x}, {y}")
    best, yaw = 1e9, 0
    for deg in range(90):
        a = math.radians(deg)
        u = near[:, 0] * math.cos(a) + near[:, 1] * math.sin(a)
        v = -near[:, 0] * math.sin(a) + near[:, 1] * math.cos(a)
        area = (u.max() - u.min()) * (v.max() - v.min())
        if area < best:
            best, yaw = area, deg
    cones.append(dict(at=[x, y, 0.0], yaw=yaw))

# The lying cone points the way the old one does, found from its own vertices: the standing cone is close enough to be caught with them.
# The tip is the narrower end. The old cone's axis climbs, leaving its tip 13 in up in the air, so this one tilts down to rest on the ground.
near = orange[(np.hypot(orange[:, 0] - LYING[0], orange[:, 1] - LYING[1]) < 32.0) & (np.hypot(orange[:, 0] - STANDING[0][0], orange[:, 1] - STANDING[0][1]) > 9.0)]
centred = near - near.mean(0)
axis = np.linalg.svd(centred, full_matrices=False)[2][0]
along = centred @ axis
spread = np.linalg.norm(centred - np.outer(along, axis), axis=1)
if spread[along > along.mean()].mean() > spread[along < along.mean()].mean():
    axis = -axis
tilt = math.atan2(6.0, 28.0)
heading = axis[:2] / np.linalg.norm(axis[:2])
lying_axis = np.array((heading[0] * math.cos(tilt), heading[1] * math.cos(tilt), -math.sin(tilt)))
# Back 3 in along its heading: at the old base's place, the new tip, now down on the ground, would go into the crate behind it.
base = np.array(LYING) - heading * 3.0
cones.append(dict(at=[round(float(base[0]), 3), round(float(base[1]), 3), round(7.0 * math.cos(tilt), 4)], axis=[round(float(c), 5) for c in lying_axis]))
middle = base + heading * 12.0
side = np.array((heading[1], -heading[0]))
if side[0] > 0:
    side = -side  # From the side away from the standing cone.
lying_eye = middle + side * 50.0

config = dict(
    width=1536,
    height=1024,
    stream_frames=90,
    settle_frames=30,
    exposure=2.5,  # The middle of the scene's own auto-exposure range (2 to 3), held still so that before and after match.
    cones=cones,
    views=[
        dict(name="player", eye=[-72, 8, 64], target=[-178, 50, 12], fov=60),  # Standing in the lane, at a player's eye height.
        dict(name="close", eye=[-132, 16, 38], target=[-166, 54, 14], fov=48),
        dict(name="lying", eye=[round(float(lying_eye[0]), 2), round(float(lying_eye[1]), 2), 26], target=[round(float(middle[0]), 2), round(float(middle[1]), 2), 6], fov=48),
        dict(name="underside", eye=[-160, 16, 30], target=[-202, 48, 7], fov=52),
        dict(name="base", eye=[-150, 36, 17], target=[-166, 54, 4], fov=46),
        dict(name="site", eye=[465, -475, 64], target=[545, -600, 14], fov=60),  # Walking onto A site.
    ],
)
with open(os.path.join(OUT, "config.json"), "w") as h:
    json.dump(config, h, indent=1)
print(json.dumps(cones))
