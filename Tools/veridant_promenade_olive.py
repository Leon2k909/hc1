"""Build the close-range Veridant promenade olive into an import staging folder."""

import math
import sys
from pathlib import Path

import numpy as np

import map_kit as K
import veridant_parts as P


RESOURCE = "models/props/shared/veridant_promenade_olive_v3"
BARK = "vr_bark"
LEAVES = {
    "leaf_shade": (0.27, 0.33, 0.20),
    "leaf_green": (0.37, 0.43, 0.28),
    "leaf_silver": (0.45, 0.49, 0.36),
}


def add_leaf(model, rng, root, direction, side, paint):
    length = rng.uniform(3.0, 4.9)
    tip = root + direction * length
    middle = root + direction * (length * 0.46)
    width = length * rng.uniform(0.12, 0.17)
    normal = P.unit(np.cross(direction, side))
    left = middle - side * width
    right = middle + side * width + normal * (width * 0.45)
    model.polygon(paint, (root, left, tip), both_sides=True)
    model.polygon(paint, (root, tip, right), both_sides=True)


def add_crown(model, rng, start, end, radius):
    paints = tuple(LEAVES)
    for _ in range(20):
        along = rng.uniform(0.02, 1.04)
        origin = start + (end - start) * along
        angle = rng.uniform(0, math.tau)
        outward = P.v(math.cos(angle), math.sin(angle), rng.uniform(-0.65, 0.95))
        twig_end = origin + outward * rng.uniform(radius * 0.35, radius * 1.25)
        P.tube(model, [origin, twig_end], [0.23, 0.07], BARK, 4)
        axis = P.unit(twig_end - origin)
        lateral = P.unit(np.cross(axis, P.UP))
        for step in range(8):
            root = origin + (twig_end - origin) * ((step + 1) / 9)
            for offset in (-1, 1):
                direction = P.unit(axis * rng.uniform(0.3, 1.1) + lateral * offset
                                   + P.UP * rng.uniform(-0.85, 0.85))
                side = P.unit(np.cross(direction, P.UP + lateral * rng.uniform(-1.2, 1.2)))
                paint = rng.choice(paints, p=(0.25, 0.53, 0.22))
                add_leaf(model, rng, root, direction, side, paint)


def build_tree():
    model = K.Model()
    rng = np.random.default_rng(73)
    trunk = [P.v(*point) for point in (
        (0, 0, -1.5), (-2, 1, 8), (-4, 2, 23), (0, 0, 39), (4, -1, 56),
    )]
    P.tube(model, trunk, [6.5, 5.4, 4.1, 3.2, 2.35], BARK, 10, cap=True)
    for angle, reach, height, join in (
        (0.1, 46, 96, 2), (1.2, 40, 109, 3), (2.3, 49, 91, 2),
        (3.25, 44, 103, 3), (4.35, 47, 88, 2), (5.4, 43, 101, 3),
        (0.75, 15, 126, 4), (3.8, 19, 120, 4),
    ):
        radial = P.v(math.cos(angle), math.sin(angle), 0)
        start = trunk[join]
        end = radial * reach + P.UP * height
        points = P.bent(start, end, -P.UP * 7, 5, rng, 2.3)
        P.tube(model, points, [2.6, 2.15, 1.65, 1.18, 0.7, 0.24], BARK, 7)
        for side in (-1, 1):
            fork_angle = angle + side * rng.uniform(0.55, 1.2)
            outward = P.v(math.cos(fork_angle), math.sin(fork_angle), 0)
            fork = points[3] + outward * rng.uniform(15, 25) + P.UP * rng.uniform(12, 25)
            elbow = points[3] * 0.4 + fork * 0.6 - P.UP * 4
            P.tube(model, [points[3], elbow, fork], [0.9, 0.54, 0.14], BARK, 5)
            add_crown(model, rng, elbow, fork, 13)
        add_crown(model, rng, points[4], end, 11)
    model.tile_overrides.update({paint: 48 for paint in (BARK, *LEAVES)})
    model.material_overrides[BARK] = "materials/veridant/vr_bark.vmat"
    model.material_overrides.update({paint: f"{RESOURCE}/{paint}.vmat" for paint in LEAVES})
    return model


def export(stage):
    stage.mkdir(parents=True, exist_ok=True)
    model = build_tree()
    for paint, (red, green, blue) in LEAVES.items():
        (stage / f"{paint}.vmat").write_text(
            '"Layer0"\n{\n    shader "shaders/complex.shader"\n'
            f'    TextureColor "[{red} {green} {blue} 1]"\n'
            '    TextureRoughness "[0.82 0.82 0.82 1]"\n}\n',
            encoding="utf-8",
        )
    K.write_obj(stage / "olive.obj", model, "olive")
    K.write_vmdl(stage / "olive.vmdl", RESOURCE, "olive", model)
    print(sum(len(points) - 2 for group in model.polygons.values() for points, _ in group))


if __name__ == "__main__":
    export(Path(sys.argv[1]))
