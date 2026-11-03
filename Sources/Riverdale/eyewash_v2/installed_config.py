"""Write capture_compare.cs.txt's config for the installed eye washes: python installed_config.py <project root> [folder name]

Views of all five where the scene puts them, from the front and from above, and a wide one on the side wall, with nothing added: what's drawn is what's installed. Reads their places from the scene.
"""
import json
import math
import os
import sys

ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "installed"
FOLDER = os.path.join(ROOT, "output/asset-improvement-20261030/eyewash/engine")
MODEL = "models/maps/riverdale/eyewash_v2/eyewash.vmdl"
scene = json.loads(open(os.path.join(ROOT, "Assets/scenes/maps/Riverdale/riverdale.scene"), encoding="utf-8").read())
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
group = next(c for c in world["Children"] if c.get("Name") == "Eye Washes")
views = [dict(name="warm_up", eye=[560, 910, 58], target=[560, 996, 32], fov=50) for _ in range(3)]
for k, item in enumerate(group["Children"]):
    x, y, z = map(float, item["Position"].split(","))
    qx, qy, qz, qw = map(float, item["Rotation"].split(","))
    yaw = 2 * math.atan2(qz, qw)
    out = (-math.sin(yaw), math.cos(yaw))
    along = (math.cos(yaw), math.sin(yaw))

    def p(u, v, h):
        return [x + along[0] * u + out[0] * v, y + along[1] * u + out[1] * v, z + h]

    views.append(dict(name=f"front_{k}_{x:.0f}_{y:.0f}", eye=p(-14, 58, 56), target=p(0, 4, 32), fov=52))
    views.append(dict(name=f"above_{k}_{x:.0f}_{y:.0f}", eye=p(-8, 26, 60), target=p(0, 7, 36), fov=46))
views.append(dict(name="wide_east_wall", eye=[640, 770, 64], target=[560, 996, 32], fov=34))
config = dict(scene="Assets/scenes/maps/Riverdale/riverdale.scene", visual=["Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes"], exposure=6.0,
              out=f"output/asset-improvement-20261030/eyewash/engine/{OUT}", width=1280, height=800, stream_frames=120, settle_frames=8, models=[MODEL], extras=[], views=views, rays=[])
json.dump(config, open(os.path.join(FOLDER, "config.json"), "w", encoding="utf-8"), indent=1)
print(len(group["Children"]), "eye washes,", len(views), "views")
