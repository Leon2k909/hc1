"""Write engine/config.json and run the capture in the shared editor's isolated scene: python capture.py <cli helper dir> [view ...]"""
import json
import os
import sys
import time

ROOT = r"C:\sbox-projects\hc1\forked-shooter-main"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, sys.argv[1])
from sb import call  # noqa: E402

ENGINE = os.path.join(ROOT, "output", "asset-improvement-20261030", "range-bench", "engine")
os.makedirs(ENGINE, exist_ok=True)
L = -450.0
VIEWS = [
    # Standing at the bench, as the game's camera does.
    dict(name="stand", eye=(-74, L, 66), target=(30, L, 22), fov=90, variants=["before", "after"]),
    # Old and new in one frame: the old bench stands on the left, the new one on the right.
    dict(name="pair", eye=(-300, -360, 92), target=(-19, -360, 26), fov=66, width=1800, height=620, variants=["mixed"]),
    dict(name="three_quarter", eye=(-92, L - 92, 58), target=(-19, L - 10, 24), fov=70, variants=["before", "after"]),
    dict(name="top", eye=(-52, L + 20, 54), target=(-14, L - 18, 33), fov=62, variants=["after"]),
    dict(name="tray", eye=(-34, L - 62, 50), target=(-20, L - 46, 34), fov=50, variants=["after"]),
    dict(name="shelf", eye=(-88, L + 62, 30), target=(-19, L + 26, 18), fov=60, variants=["after"]),
    dict(name="downrange", eye=(62, L + 70, 54), target=(-19, L, 24), fov=70, variants=["before", "after"]),
    dict(name="far12m", eye=(-470, L - 300, 80), target=(-19, L, 24), fov=50, variants=["before", "after"]),
]
wanted = set(sys.argv[2:])
views = [v for v in VIEWS if not wanted or v["name"] in wanted]
with open(os.path.join(ENGINE, "config.json"), "w") as h:
    json.dump(dict(width=1600, height=900, exposure=1.5, stream_frames=70, settle_frames=14, views=views), h)
started = time.time()
print(call("run_csharp", {"path": os.path.join(HERE, "capture_engine.cs.txt")}, timeout=175)[:1500].strip(), f"{time.time() - started:.0f}s")
