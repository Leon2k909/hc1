"""Write capture_compare.cs.txt's config: python compare_config.py <project root> [folder name]

The old stand as the game draws it, and the new one stood 46 in along from it in the isolated scene, at the same turn, under the hall's own lights. Both are in every frame,
so neither gets a kinder exposure. Close up, from behind, and from further off.
"""
import json
import math
import os
import sys

ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "pass1"
FOLDER = os.path.join(ROOT, "output/asset-improvement-20261030/info-stand/engine")
os.makedirs(FOLDER, exist_ok=True)
MODEL = "models/maps/reefhall/info_stand_v2/info_stand.vmdl"
GAP = 46.0


def world(e, n, z):
    # Plan (e, n, z) is engine (n, -e, z).
    return [n, -e, z]


def frame_of(centre, yaw):
    d = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
    f = (-d[1], d[0])

    def at(u, w, z):
        return world(centre[0] + d[0] * u + f[0] * w, centre[1] + d[1] * u + f[1] * w, z)

    return at


t = math.radians(250)
centre = (360 * math.cos(t), 360 * math.sin(t))
yaw = 340.0
at = frame_of(centre, yaw)
# Engine yaw for a model with its width on +X and its front on +Y, where the map's frame has u along yaw and w to its left.
engine_yaw = yaw - 90.0
extras = [dict(model=MODEL, at=at(GAP, 0, 0), yaw=engine_yaw)]
mid = GAP / 2
views = [
    dict(name="pair_front", eye=at(mid, 84, 60), target=at(mid, 0, 25), fov=60),
    dict(name="pair_three_quarter", eye=at(mid - 74, 92, 62), target=at(mid, 0, 25), fov=46),
    dict(name="pair_other_side", eye=at(mid + 80, 86, 62), target=at(mid, 0, 25), fov=46),
    dict(name="pair_back", eye=at(mid + 40, -104, 66), target=at(mid, 0, 25), fov=46),
    dict(name="new_close", eye=at(GAP - 16, 46, 58), target=at(GAP, 0, 30), fov=48),
    dict(name="new_plate", eye=at(GAP + 10, 24, 30), target=at(GAP, 2, 20), fov=44),
    dict(name="new_foot", eye=at(GAP - 14, 34, 22), target=at(GAP, 2, 4), fov=46),
    dict(name="new_back", eye=at(GAP + 18, -36, 40), target=at(GAP, 0, 26), fov=50),
    # The central tank stands in front of them, so the far shots look along the floor and in from the south hall.
    dict(name="pair_12m", eye=at(mid + 472, 70, 64), target=at(mid, 0, 25), fov=32),
    dict(name="pair_20m", eye=world(53, -1107, 64), target=at(mid, 0, 25), fov=24),
    dict(name="pair_35m", eye=world(303, -1643, 64), target=at(mid, 0, 25), fov=18),
]
config = dict(scene="Assets/scenes/maps/ReefHall/reefhall.scene", visual=["Ambient", "Fog", "Aquarium", "Lights", "Reflection Probes"], exposure=1.0,
              out=f"output/asset-improvement-20261030/info-stand/engine/{OUT}", width=1280, height=800, stream_frames=120, settle_frames=8, models=[MODEL], extras=extras, views=views, rays=[])
json.dump(config, open(os.path.join(FOLDER, "config.json"), "w", encoding="utf-8"), indent=1)
print(len(views), "views", extras)
