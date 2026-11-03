"""Write capture_compare.cs.txt's config: python compare_config.py <project root> [folder name]

Riverdale's old eye wash at n 560 on the hall's east wall as the game draws it, and the new one stood 50 in along from it in the isolated scene, at the wall's turn, under the hall's own lights. Both are in
the pair shots, so neither gets a kinder exposure. Engine coordinates: that wall is at y 1000 and faces -y.
"""
import json
import os
import sys

ROOT = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "pass1"
FOLDER = os.path.join(ROOT, "output/asset-improvement-20261030/eyewash/engine")
os.makedirs(FOLDER, exist_ok=True)
MODEL = "models/maps/riverdale/eyewash_v2/eyewash.vmdl"
OLD_N, NEW_N, WALL = 560.0, 610.0, 1000.0
# The walls' epoxy band stands 0.25 in proud of the wall, and it swallowed the bracket's plate until the model stood on the band.
extras = [dict(model=MODEL, at=[NEW_N, WALL - 0.25, 0.0], yaw=180.0)]
mid = (OLD_N + NEW_N) / 2
views = [
    # The tonemapper takes a moment to reach its held exposure, so the first frames are thrown away.
    dict(name="warm_up", eye=[mid, WALL - 86, 58], target=[mid, WALL - 4, 32], fov=50),
    dict(name="warm_up", eye=[mid, WALL - 86, 58], target=[mid, WALL - 4, 32], fov=50),
    dict(name="warm_up", eye=[mid, WALL - 86, 58], target=[mid, WALL - 4, 32], fov=50),
    dict(name="pair", eye=[mid, WALL - 86, 58], target=[mid, WALL - 4, 32], fov=50),
    dict(name="pair_low", eye=[mid - 20, WALL - 70, 24], target=[mid, WALL - 4, 32], fov=56),
    dict(name="new_front", eye=[NEW_N, WALL - 46, 52], target=[NEW_N, WALL - 4, 30], fov=46),
    dict(name="new_above", eye=[NEW_N + 8, WALL - 26, 60], target=[NEW_N, WALL - 7, 36], fov=46),
    dict(name="new_under", eye=[NEW_N - 14, WALL - 34, 16], target=[NEW_N, WALL - 5, 32], fov=52),
    dict(name="new_side", eye=[NEW_N - 40, WALL - 20, 44], target=[NEW_N, WALL - 7, 32], fov=46),
    dict(name="old_above", eye=[OLD_N + 8, WALL - 26, 60], target=[OLD_N, WALL - 7, 36], fov=46),
    dict(name="old_front", eye=[OLD_N, WALL - 46, 52], target=[OLD_N, WALL - 4, 30], fov=46),
    dict(name="pair_6m", eye=[mid + 60, WALL - 230, 64], target=[mid, WALL - 4, 32], fov=34),
    dict(name="pair_12m", eye=[mid + 160, WALL - 440, 64], target=[mid, WALL - 4, 32], fov=22),
]
config = dict(scene="Assets/scenes/maps/Riverdale/riverdale.scene", visual=["Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes"], exposure=6.0,
              out=f"output/asset-improvement-20261030/eyewash/engine/{OUT}", width=1280, height=800, stream_frames=120, settle_frames=8, models=[MODEL], extras=extras, views=views, rays=[])
json.dump(config, open(os.path.join(FOLDER, "config.json"), "w", encoding="utf-8"), indent=1)
print(len(views), "views")
