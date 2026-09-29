"""Build the compact raised rail that sits on the stock S&box MP5 claw mount."""

from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "Assets/attachments/mpapa5/optic_riser"
OUT.mkdir(parents=True, exist_ok=True)

vertices = []
uvs = []
normals = []
faces = []


def face(points):
    # Source model space is forward/side/up. The OBJ importer reads side/up/forward.
    a, b, c = points[:3]
    u = tuple(b[i] - a[i] for i in range(3))
    v = tuple(c[i] - a[i] for i in range(3))
    n = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    start = len(vertices) + 1
    for p, uv in zip(points, ((0, 0), (1, 0), (1, 1), (0, 1))):
        vertices.append((p[1], p[2], p[0]))
        uvs.append(uv)
        normals.append((n[1], n[2], n[0]))
    faces.append(tuple(range(start, start + 4)))


def box(x0, x1, y0, y1, z0, z1):
    p = (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    )
    for indices in ((3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4),
                    (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        face([p[i] for i in indices])


def build(name, front):
    vertices.clear()
    uvs.clear()
    normals.clear()
    faces.clear()

    # The rear base grips the MP5's native claw rail. The long variant also
    # supports the 2x magnifier's (att_vm_2x_west01) separate forward mini dot over the handguard.
    box(-0.25, 3.50, -0.49, 0.49, 10.00, 10.16)
    if front > 3.50:
        box(3.50, front, -0.49, 0.49, 10.00, 10.16)

    supports = [(-0.05, 0.65), (2.55, 3.25)]
    if front > 3.50:
        supports.append((6.15, 6.80))
    for x0, x1 in supports:
        for y0, y1 in ((-0.43, -0.25), (0.25, 0.43)):
            box(x0, x1, y0, y1, 10.15, 10.20)

    if front > 3.50:
        # A pair of feet meets the top of the original handguard so the
        # forward reflex sight and its extended rail do not float in profile.
        for y0, y1 in ((-0.48, -0.30), (0.30, 0.48)):
            box(6.15, 6.80, y0, y1, 9.50, 10.16)

    box(-0.25, front, -0.42, 0.42, 10.18, 10.23)
    for i in range(8 if front == 3.50 else 15):
        x = -0.21 + i * 0.50
        box(x, min(x + 0.28, front), -0.52, 0.52, 10.22, 10.27)

    lines = ["mtllib optic_riser.mtl", f"o {name}"]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in vertices]
    lines += [f"vt {u:.6f} {v:.6f}" for u, v in uvs]
    lines += [f"vn {x:.6f} {y:.6f} {z:.6f}" for x, y, z in normals]
    lines += ["usemtl riser_metal"]
    for indices in faces:
        a, b, c, d = indices
        for tri in ((a, b, c), (a, c, d)):
            lines.append("f " + " ".join(f"{i}/{i}/{i}" for i in tri))
    (OUT / f"{name}.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")


build("optic_riser", 3.50)
build("optic_riser_long", 7.05)
(OUT / "optic_riser_long.vmdl").write_text(
    (OUT / "optic_riser.vmdl").read_text(encoding="utf-8").replace(
        "optic_riser.obj", "optic_riser_long.obj"
    ),
    encoding="utf-8",
)
(OUT / "optic_riser.mtl").write_text(
    "newmtl riser_metal\nKd 0.12 0.13 0.14\nKa 0 0 0\nKs 0.2 0.2 0.2\n",
    encoding="utf-8",
)
