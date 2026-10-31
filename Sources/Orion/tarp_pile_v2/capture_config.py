"""Write the engine comparison's config: python capture_config.py <project root>. The pile stands at the old one's place and heading, plan (195, 0) along (1, 0.2). Plan (e, n, z) is engine (n, -e, z)."""
import json
import math
import os
import sys

ROOT = sys.argv[1]
OUT = os.path.join(ROOT, "output/asset-improvement-20261030/tarp-pile/engine")
os.makedirs(OUT, exist_ok=True)


def w(p):
    return [p[1], -p[0], p[2]]


views = [
    ("near", (60, -110, 64), (195, 0, 30), 55),
    ("side", (330, -90, 64), (195, 0, 30), 55),
    ("back", (120, 150, 64), (195, 0, 30), 55),
    ("top", (110, -70, 130), (195, 0, 24), 55),
    ("hem", (118, -44, 26), (150, -22, 8), 48),
    ("close", (105, -30, 60), (160, 0, 36), 48),
    ("far", (-160, -180, 64), (195, 0, 30), 30),
]
config = dict(exposure=1.3, width=1280, height=800, stream_frames=120, settle_frames=8, at=w((195.0, 0.0, 0.0)), yaw=math.degrees(math.atan2(0.2, 1.0)),
              views=[dict(name=n, eye=w(e), target=w(t), fov=f) for n, e, t, f in views])
json.dump(config, open(os.path.join(OUT, "config.json"), "w", encoding="utf-8"), indent=1)
print(len(views), "views")
