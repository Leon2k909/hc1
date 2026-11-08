"""Fit the reconstructed prototype lion and model its carved limestone mount."""
from math import cos, pi, sin
from pathlib import Path
import sys

import fast_simplification
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "Assets/models/props/shared/veridant_fountain_reference_top"
BRONZE = "reference_bronze"
STONE = "carved_limestone"
FORWARD = np.array((.6, -.8, 0))
LEFT = np.array((.8, .6, 0))
BASIS = np.column_stack((FORWARD, LEFT, (0, 0, 1)))


def fit_lion(source):
    model = trimesh.load_mesh(source)
    model = max(model.split(only_watertight=False), key=lambda part: len(part.faces))
    vertices, faces = fast_simplification.simplify(
        np.ascontiguousarray(model.vertices), np.ascontiguousarray(model.faces),
        target_count=55000,
    )
    # Use the long axis of the horizontal projection to align both pairs of paws.
    yaw = -.096
    x, up, z = vertices.T
    depth = cos(yaw) * x + sin(yaw) * z
    across = sin(yaw) * x - cos(yaw) * z
    points = np.column_stack((
        1.4 + (depth - depth.min()) * (32.5 / np.ptp(depth)),
        (across - (across.min() + across.max()) / 2) * 16.7,
        49.25 + (up - up.min()) * (27.45 / np.ptp(up)),
    ))
    mesh = trimesh.Trimesh(points, faces, process=False)
    mesh.fix_normals()
    trimesh.smoothing.filter_taubin(mesh, lamb=.46, nu=.50, iterations=6)
    delta = mesh.vertices - points
    mesh.vertices = points + delta * np.minimum(1, .18 / np.maximum(1e-8, np.linalg.norm(delta, axis=1)))[:, None]
    return mesh


def perimeter(rx, ry, exponent, angle):
    x, y = cos(angle), sin(angle)
    return (rx * np.copysign(abs(x) ** (2 / exponent), x),
            ry * np.copysign(abs(y) ** (2 / exponent), y))


def moulding(profile, centre=0, exponent=3, sides=96):
    """Closed swept stone or bronze profile with a separate planar top."""
    vertices = [(centre + x, y, z) for z, rx, ry in profile for x, y in
                (perimeter(rx, ry, exponent, i * 2 * pi / sides) for i in range(sides))]
    faces = []
    for row in range(len(profile) - 1):
        for i in range(sides):
            a = row * sides + i
            b = row * sides + (i + 1) % sides
            faces.extend(((a, b, a + sides), (b, b + sides, a + sides)))
    sides_mesh = trimesh.Trimesh(vertices, faces, process=False)
    uv = [(i / sides * 3, z / 24) for z, _, _ in profile for i in range(sides)]
    caps = []
    for index, sign in ((0, -1), (-1, 1)):
        z, rx, ry = profile[index]
        ring = [(centre + x, y, z) for x, y in
                (perimeter(rx, ry, exponent, i * 2 * pi / sides) for i in range(sides))]
        faces = [(0, 1 + i, 1 + (i + 1) % sides) for i in range(sides)]
        if sign < 0:
            faces = [face[::-1] for face in faces]
        cap = trimesh.Trimesh([(centre, 0, z), *ring], faces, process=False)
        caps.append((cap, cap.vertices[:, :2] / 24))
    return [(sides_mesh, uv), *caps]


PIER = [
    (47.8, 6.3, 10.6), (48.45, 6.8, 11.0), (49.3, 6.8, 11.0),
    (49.6, 6.35, 10.52), (50.25, 6.14, 10.26), (50.65, 5.86, 9.98),
    (51.35, 5.63, 9.62), (53, 5.05, 9.08), (55.5, 4.7, 8.78),
    (58, 4.66, 8.59), (60.5, 4.78, 8.52), (63, 4.99, 8.5),
    (65.5, 5.4, 8.53), (68, 5.94, 8.64), (70.5, 6.54, 8.82),
    (73, 7.2, 9.12), (75.5, 7.9, 9.42), (77.25, 8.46, 9.72),
    (77.7, 8.69, 9.93), (78.1, 9.3, 10.43), (78.6, 9.4, 10.55),
    (78.95, 9.75, 10.86), (79.35, 10.5, 11.37), (79.95, 10.86, 11.68),
    (80.45, 10.72, 11.57), (80.8, 10.4, 11.27), (80.98, 9.94, 10.96),
]
PIER_EXPONENT = 3.45
PIER_HEIGHTS, PIER_WIDTHS, PIER_DEPTHS = np.array(PIER).T


def face_at(x, z):
    width = np.interp(z, PIER_HEIGHTS, PIER_WIDTHS)
    depth = np.interp(z, PIER_HEIGHTS, PIER_DEPTHS)
    return depth * max(0, 1 - (abs(x) / width) ** PIER_EXPONENT) ** (1 / PIER_EXPONENT)


def carving(side, centreline, profile, length=30, columns=16):
    """Raise a lobed leaf or a moulded border from the curved pier face."""
    positions, uvs, faces = [], [], []
    for row in range(length + 1):
        t = row / length
        x, z = centreline(t)
        for col in range(columns + 1):
            u = 2 * col / columns - 1
            width, lift = profile(t, u)
            dx = x + width * u
            y = side * (face_at(dx, z) + lift)
            positions.append((dx, y, z))
            uvs.append((dx / 22, z / 22))
            if row < length and col < columns:
                a = row * (columns + 1) + col
                b = a + columns + 1
                faces.extend(((a, b, a + 1), (a + 1, b, b + 1)))
    if side < 0:
        faces = [f[::-1] for f in faces]
    return trimesh.Trimesh(positions, faces, process=False), uvs


def acanthus(side):
    def stem_x(z):
        return .38 * sin((z - 52) * .28) + .32 * (z - 64) / 12

    def stem_profile(t, u):
        return .36 - .21 * t, .44 * (1 - u * u) - .025

    yield carving(side, lambda t: (stem_x(51.5 + 25.4 * t), 51.5 + 25.4 * t), stem_profile)

    for left, start, length, reach in (
        (-1, 52.8, 6.2, 2.58), (1, 54.4, 7.3, 2.58),
        (-1, 57.7, 8.4, 3.05), (1, 60.5, 8.6, 3.62),
        (-1, 64.1, 9.35, 3.94), (1, 67.6, 9.1, 4.08), (-1, 71.0, 7.15, 1.22),
    ):
        def line(t):
            return (stem_x(start) + left * reach * (sin(t * 2.12) ** 1.24), start + length * t)

        def blade(t, u):
            spread = sin(pi * t) ** .88
            lobes = .79 + .21 * cos(t * 9 * pi - .42)
            width = .08 + (1.07 + reach * .14) * spread * lobes
            vein = 1 - u * u
            curl = sin(t * 14.4 - abs(u) * 3) * .11
            lift = spread * (vein ** 1.45 * (.57 + curl) + .27 * vein ** 6) - .035
            return width, lift

        yield carving(side, line, blade)

    for left in (-1, 1):
        def frame(t):
            z = 50.55 + 27.55 * t
            half_width = np.interp(z, PIER_HEIGHTS, PIER_WIDTHS)
            return left * (.77 * half_width), z

        def trim(t, u):
            return .35 + .13 * t, (.41 + .16 * t) * (1 - u * u) ** .6 - .045

        yield carving(side, frame, trim, length=48, columns=10)


def write_obj(assets):
    with (FOLDER / "crown.obj").open("w", encoding="utf-8") as obj:
        obj.write("mtllib crown.mtl\n")
        offset = 1
        for name, material, mesh, uv, sign in assets:
            basis = BASIS * np.array((sign, sign, 1))
            obj.write(f"o {name}\nusemtl {material}\n")
            for x, y, z in mesh.vertices @ basis.T:
                obj.write(f"v {y:.5f} {z:.5f} {x:.5f}\n")
            for u, v in uv:
                obj.write(f"vt {u:.5f} {v:.5f}\n")
            for x, y, z in mesh.vertex_normals @ basis.T:
                obj.write(f"vn {y:.5f} {z:.5f} {x:.5f}\n")
            for face in mesh.faces + offset:
                obj.write("f " + " ".join(f"{i}/{i}/{i}" for i in face) + "\n")
            offset += len(mesh.vertices)


def main(source):
    FOLDER.mkdir(parents=True, exist_ok=True)
    lion = fit_lion(source)
    assets = []
    pads = moulding([(47, 17, 9.2), (47.7, 17.3, 9.45), (48.7, 17.3, 9.45),
                     (49.22, 16.8, 8.97), (49.42, 16.55, 8.68)], centre=17.5, exponent=3.6)
    for sign in (1, -1):
        assets.append((f"lion_{sign}", BRONZE, lion, lion.vertices[:, [0, 2]] / 32, sign))
        assets.extend((f"pad_{sign}_{i}", BRONZE, mesh, uv, sign) for i, (mesh, uv) in enumerate(pads))
    assets.extend((f"pier_{i}", STONE, mesh, uv, 1) for i, (mesh, uv) in enumerate(moulding(PIER, exponent=PIER_EXPONENT)))
    for side in (1, -1):
        assets.extend((f"relief_{side}_{i}", STONE, mesh, uv, 1) for i, (mesh, uv) in enumerate(acanthus(side)))
    write_obj(assets)
    (FOLDER / "crown.mtl").write_text(f"newmtl {BRONZE}\nKd 0.18 0.12 0.07\nnewmtl {STONE}\nKd 0.58 0.47 0.33\n", encoding="utf-8")
    template = ROOT / "Assets/models/props/shared/veridant_fountain_sculpture_v4/sculpture.vmdl"
    model = template.read_text(encoding="utf-8-sig")
    model = model.replace("veridant_fountain_sculpture_v4/sculpture.obj", FOLDER.name + "/crown.obj")
    model = model.replace("reclining_lions", "reference_fountain_crown")
    model = model.replace('from = "lion_bronze.vmat" to = "materials/veridant/fountain_weathered_bronze.vmat"',
                          f'from = "{BRONZE}.vmat" to = "materials/veridant/fountain_reference_bronze.vmat"')
    model = model.replace('materials/veridant/fountain_reference_bronze.vmat" }',
                          'materials/veridant/fountain_reference_bronze.vmat" },\n'
                          '\t\t\t\t\t\t\t{ from = "carved_limestone.vmat" to = "materials/veridant/fountain_reference_limestone.vmat" }')
    (FOLDER / "crown.vmdl").write_text(model, encoding="utf-8")
    print(f"Lion {len(lion.faces):,} triangles, full crown {sum(len(mesh.faces) for _, _, mesh, _, _ in assets):,}")
    print(f"Lion bounds in radial, lateral, height coordinates: {lion.bounds.tolist()}")


if __name__ == "__main__":
    main(sys.argv[1])
