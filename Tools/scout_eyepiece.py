"""Seal the Scout 3x rear bezel without changing its lens, reticle, or mount.

The imported rear liner stops at radius 0.468 while the housing starts at
0.495, leaving daylight between them. This closed, bevelled collar overlaps
both parts. ModelDoc converts OBJ (x, y, z) to model (z, x, y).
"""

from collections import Counter
from math import cos, sin, tau, hypot
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MESH = ROOT / "Assets/attachments/m4a1/optics/scout_indexed.obj"
BEGIN = b"# BEGIN Scout eyepiece collar\n"
END = b"# END Scout eyepiece collar\n"
SEGMENTS = 64
CENTER = (-0.0425439, 1.0682995)
# (model longitudinal position, radial distance). The return path closes
# the collar, including an inward-facing wall and front/rear annular faces.
PROFILE = (
    (-4.699, 0.454),
    (-4.699, 0.497),
    (-4.686, 0.512),
    (-4.456, 0.512),
    (-4.456, 0.358),
    (-4.681, 0.444),
)


def main():
    current = MESH.read_bytes()
    original = current
    if BEGIN in original:
        assert original.count(BEGIN) == 1 and original.endswith(END)
        original = original.split(BEGIN, 1)[0]
    if not original.endswith(b"\n"):
        original += b"\n"

    counts = Counter(line.split(b" ", 1)[0] for line in original.splitlines())
    vertices, normals, uvs, faces = [], [], [], []

    for edge, (depth, radius) in enumerate(PROFILE):
        next_depth, next_radius = PROFILE[(edge + 1) % len(PROFILE)]
        dr, dz = next_radius - radius, next_depth - depth
        length = hypot(dr, dz)
        start = len(vertices)
        for end_depth, end_radius in ((depth, radius), (next_depth, next_radius)):
            for segment in range(SEGMENTS):
                angle = tau * segment / SEGMENTS
                c, s = cos(angle), sin(angle)
                vertices.append((CENTER[0] + end_radius * c,
                                 CENTER[1] + end_radius * s, end_depth))
                # Outward profile normal; inner wall faces the aperture.
                normals.append((dz * c / length, dz * s / length, -dr / length))
                uvs.append((segment / SEGMENTS, float(end_depth == next_depth and end_radius == next_radius)))
        for segment in range(SEGMENTS):
            a = start + segment
            b = start + SEGMENTS + segment
            c = start + SEGMENTS + (segment + 1) % SEGMENTS
            d = start + (segment + 1) % SEGMENTS
            faces.extend(((a, c, b), (a, d, c)))

    # Hard edges use split shading vertices. Weld positions for the closure
    # check so every physical edge belongs to exactly two triangles.
    weld = [tuple(round(x, 7) for x in v) for v in vertices]
    physical_edges = Counter()
    for face in faces:
        a, b, c = (vertices[i] for i in face)
        ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = (ab[1] * ac[2] - ab[2] * ac[1],
                 ab[2] * ac[0] - ab[0] * ac[2],
                 ab[0] * ac[1] - ab[1] * ac[0])
        assert sum(cross[i] * normals[face[0]][i] for i in range(3)) > 0
        for i in range(3):
            physical_edges[tuple(sorted((weld[face[i]], weld[face[(i + 1) % 3]])))] += 1
    assert set(physical_edges.values()) == {2}, "Collar must be a closed solid"

    block = [BEGIN.decode().rstrip(), "g scout_eyepiece_collar", "s 1"]
    for v, uv, normal in zip(vertices, uvs, normals):
        block.append("v " + " ".join(f"{value:.8f}" for value in v))
        block.append("vt " + " ".join(f"{value:.8f}" for value in uv))
        block.append("vn " + " ".join(f"{value:.8f}" for value in normal))
    block.append("usemtl optic_lens_baffle")
    for face in faces:
        block.append("f " + " ".join(
            f"{counts[b'v'] + i + 1}/{counts[b'vt'] + i + 1}/{counts[b'vn'] + i + 1}"
            for i in face))
    block.append(END.decode().rstrip())
    result = original + ("\n".join(block) + "\n").encode()
    if result != current:
        MESH.write_bytes(result)
    print(f"Scout bezel sealed: {len(faces)} triangles; original geometry and lens preserved.")


if __name__ == "__main__":
    main()
