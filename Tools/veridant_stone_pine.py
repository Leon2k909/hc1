"""The terrace pine: branching wood and separate, volumetric mountain-pine sprays.

The needle geometry is a local snapshot of the installed Facepunch pine_shrub_wide
model, retaining its cloud material. No collision or scene objects are added.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

PAINT = "vr_stone_pine_needles"
MATERIAL = "models/sbox_props/shrubs/pine/mountain_pine.vmat"
PACKAGE = "facepunch.pine_shrub_wide#145484"
SOURCE = Path(__file__).resolve().parent.parent / "Sources/Veridant/stone-pine-v2/pine-cluster.json"


@lru_cache(maxsize=1)
def cluster_source():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    positions = np.array([v["Position"] for v in data["Vertices"]], dtype=float)
    normals = np.array([v["Normal"] for v in data["Vertices"]], dtype=float)
    # Source world (north, west, up) to the generator's plan (east, north, up).
    positions = positions[:, [1, 0, 2]] * (-1, 1, 1)
    normals = normals[:, [1, 0, 2]] * (-1, 1, 1)
    positions -= (positions.min(axis=0) + positions.max(axis=0)) * 0.5
    uv = np.array([v["UV"] for v in data["Vertices"]], dtype=float)
    return positions, normals, uv, np.array(data["Indices"], dtype=int).reshape(-1, 3)


def cluster(model, centre, yaw, tilt, scale):
    positions, normals, uv, indices = cluster_source()
    ca, sa, ct, st = math.cos(yaw), math.sin(yaw), math.cos(tilt), math.sin(tilt)
    rotation = np.array(((ca, -sa, 0), (sa, ca, 0), (0, 0, 1))) @ np.array(((ct, 0, st), (0, 1, 0), (-st, 0, ct)))
    positions = (positions * scale) @ rotation.T + centre
    normals = (normals / scale) @ rotation.T
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
    model.material_overrides[PAINT] = MATERIAL
    model.tile_overrides[PAINT] = 1.0  # Explicit atlas UVs replace the writer's provisional mapping.
    for triangle in indices:
        model.polygon(PAINT, positions[triangle], uv=uv[triangle], normals=normals[triangle])


def stone_pine(model, base, h=560.0, crown_r=230.0, seed=0, lean=(0.0, 0.0)):
    import veridant_parts as P

    rng = np.random.default_rng(abs(int(seed)))
    b, up = P.v(*base), P.UP
    fork = b + P.v(lean[0], lean[1], 0) + up * (h * 0.62)
    # Keep the original planted trunk, its lean, and all five primary limbs.
    P.tube(model, P.bent(b, fork, P.v(lean[0] * .3, lean[1] * .3, 0) + P.v(*rng.normal(0, 8, 2), 0), 5, rng, 2.0),
           [11.0, 9.6, 8.6, 7.8, 7.0, 6.4], "vr_bark", 9)
    crown = b + P.v(lean[0] * 1.2, lean[1] * 1.2, 0) + up * (h * .84)
    limbs = []
    for k in range(5):
        angle = 2 * math.pi * k / 5 + rng.uniform(-.3, .3)
        tip = crown + P.v(math.cos(angle), math.sin(angle), 0) * (crown_r * rng.uniform(.45, .7)) - up * (h * .04)
        P.tube(model, P.bent(fork, tip, up * (h * .05), 3), [5.5, 4.4, 3.4, 2.4], "vr_bark", 6)
        limbs.append((angle, tip))

    # Distinct lobes with air between them; each lobe is a real 3D needle spray.
    # Two staggered sprays per limb leave a broken, asymmetric umbrella outline.
    size = crown_r / 240.0
    for angle, tip in limbs:
        for side in (-1, 1):
            a = angle + side * rng.uniform(.20, .36)
            reach = crown_r * rng.uniform(.59, .80)
            centre = crown + P.v(math.cos(a) * reach, math.sin(a) * reach, h * rng.uniform(-.035, .065))
            attach = centre - up * (h * .045)
            bend = up * rng.uniform(5, 14) + P.v(-math.sin(a), math.cos(a), 0) * rng.uniform(-10, 10)
            P.tube(model, P.bent(tip, attach, bend, 3), [2.5, 1.9, 1.1, .45], "vr_bark", 6, cap=True)
            scale = np.array((rng.uniform(1.20, 1.48), rng.uniform(1.00, 1.30), rng.uniform(.72, 1.00))) * size
            cluster(model, centre, a + rng.uniform(-.7, .7), rng.uniform(-.32, .32), scale)

    # A few higher inner sprays prevent the crown becoming a hollow ring.
    for k in range(3):
        a = k * 2 * math.pi / 3 + rng.uniform(-.4, .4)
        r = crown_r * rng.uniform(.12, .32)
        centre = crown + P.v(math.cos(a) * r, math.sin(a) * r, h * rng.uniform(.05, .11))
        P.tube(model, P.bent(fork, centre - up * 15, P.v(-math.sin(a) * 14, math.cos(a) * 14, 8), 4),
               [3.4, 2.7, 1.9, 1.1, .4], "vr_bark", 6, cap=True)
        cluster(model, centre, a, rng.uniform(-.22, .22), np.array((1.35, 1.20, .94)) * size)
