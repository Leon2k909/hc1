"""Boxyard perimeter wall v1: writes the textures, materials and models (boxyard-model session, 2026-11-06).

    python build.py            textures + vmats first, then the OBJs, the vmdls last (the editor compiles files as they land)
    python build.py layout     prints the 56 instances (name, model, engine position, yaw)

Models (Assets/models/props/boxyard/perimeter_wall_v1/), three LODs each (switch thresholds 0 / 36 / 110):
    perimeter_panel_a_v1, _b_v1   pitch 228.571 (the north and south runs)
    perimeter_panel_c_v1, _d_v1   pitch 240     (the east and west runs)
    perimeter_pier_a_v1, _b_v1    the concrete pier with its steel bracket
No collision: the yard model keeps the wall's four collision boxes.
"""
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pw_geom as G                                   # noqa: E402

ROOT = HERE.parents[2]
MODEL_DIR = "models/props/boxyard/perimeter_wall_v1"
OUT = ROOT / "Assets" / MODEL_DIR
THRESHOLDS = [0.0, 36.0, 110.0]

MODELS = {
    "perimeter_panel_a_v1": ("panel", 800.0 / 3.5, 101),
    "perimeter_panel_b_v1": ("panel", 800.0 / 3.5, 102),
    "perimeter_panel_c_v1": ("panel", 240.0, 103),
    "perimeter_panel_d_v1": ("panel", 240.0, 104),
    "perimeter_pier_a_v1": ("pier", None, 201),
    "perimeter_pier_b_v1": ("pier", None, 202),
}

# The old wall's runs (Tools/boxyard_map.py WALL_RUNS): name, inward normal, left end, right end of the inner face (plan e, n).
RUNS = [
    ("East", (-1.0, 0.0), (800.0, 840.0), (800.0, -840.0)),
    ("West", (1.0, 0.0), (-800.0, -840.0), (-800.0, 840.0)),
    ("North", (0.0, -1.0), (-800.0, 832.0), (800.0, 832.0)),
    ("South", (0.0, 1.0), (800.0, -832.0), (-800.0, -832.0)),
]
PANELS = 7


def engine_yaw(along_plan):
    """ Model +x (along the wall) on the engine's +x/+y axes: plan (e, n) is engine (n, -e). """
    ex, ey = along_plan[1], -along_plan[0]
    yaw = math.degrees(math.atan2(ey, ex))
    return 180.0 if abs(yaw + 180.0) < 1e-9 else (0.0 if abs(yaw) < 1e-9 else yaw)


def layout():
    """ [ ( name, model stem, ( x, y, z ) engine inches, yaw degrees ) ]: a panel and a pier at each post of each run. East and
    west runs get a pier at every post (8), north and south at the six inner ones (their ends butt into the east/west
    runs, as the old wall's did). """
    items = []
    for name, normal, left, right in RUNS:
        a0, b0 = np.array(left, float), np.array(right, float)
        along = (b0 - a0) / np.linalg.norm(b0 - a0)
        yaw = engine_yaw(along)
        ns = name in ("North", "South")
        panel_stems = ("perimeter_panel_a_v1", "perimeter_panel_b_v1") if ns else ("perimeter_panel_c_v1", "perimeter_panel_d_v1")
        for k in range(PANELS + 1):
            c = a0 + (b0 - a0) * k / PANELS
            pos = (round(float(c[1]), 4), round(float(-c[0]), 4), 0.0)
            if k < PANELS:
                items.append((f"{name} Panel {k + 1}", panel_stems[k % 2], pos, yaw))
            if not (ns and k in (0, PANELS)):
                items.append((f"{name} Pier {k + 1}", ("perimeter_pier_a_v1", "perimeter_pier_b_v1")[k % 2], pos, yaw))
    return items


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.replace("\r\n", "\n").encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return False
    temp = path.with_name(path.name + ".writing")
    temp.write_bytes(data)
    for attempt in range(20):
        try:
            temp.replace(path)
            return True
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.5)
    return True


def build_models():
    written, stats = [], {}
    for stem, (kind, pitch, seed) in MODELS.items():
        lods = []
        for lod in range(3):
            mesh = G.panel(pitch, seed, lod) if kind == "panel" else G.pier(seed, lod)
            lods.append(mesh)
            name = f"{stem}_lod{lod}"
            atomic_write(OUT / f"{name}.obj", G.obj_text(mesh, name, f"{name}.mtl"))
            mats = sorted({m for m, _, _, _ in mesh.polys})
            atomic_write(OUT / f"{name}.mtl", G.mtl_text(mats))
        stats[stem] = [m.triangles() for m in lods]
        written.append(stem)
    # vmdls last
    for stem in written:
        mats = sorted({m for lod in range(3) for m, _, _, _ in (G.panel(MODELS[stem][1], MODELS[stem][2], lod)
                                                                 if MODELS[stem][0] == "panel" else G.pier(MODELS[stem][2], lod)).polys})
        atomic_write(OUT / f"{stem}.vmdl", G.vmdl_text(MODEL_DIR, stem, mats, THRESHOLDS))
    return stats


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "layout":
        for item in layout():
            print(item)
        print(len(layout()), "instances")
        raise SystemExit
    import pw_tex as T
    T.build()
    T.write_vmats()
    print("textures and materials written")
    print(build_models())
