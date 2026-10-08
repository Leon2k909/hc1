"""Add an opaque inner ocular sleeve to the 6x Marksman scope.

The imported shell has no inward-facing surface through most of its rear
tube. Removing the original opaque lens mask exposed daylight through that
shell when viewed off-axis. The sleeve restores a physical bore and black
side occlusion without changing the glass, reticle, bodygroups or aim offsets.

Run: python Tools/marksman_scope_baffle.py
"""

from collections import Counter
from math import cos, sin, tau, hypot
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = "attachments/mw2022/models/att_vm_scope_mike14"
FOLDER = ROOT / "Assets" / RESOURCE
STEM = "att_vm_scope_mike14"
SEGMENTS = 64
CENTER = (-0.003, 1.317)  # Model lateral/up axes; OBJ imports as model (z,x,y).
# Closed longitudinal/radial cross-section. Outer walls sit inside the shell;
# the inner wall faces the bore, with an annular diaphragm at its front.
PROFILE = (
    (-3.460, 0.664),
    (-3.460, 0.718),
    (-0.750, 0.652),
    (-0.710, 0.635),
    (-0.710, 0.530),
    (-0.760, 0.550),
    (-3.380, 0.664),
)


def write_changed(path, content):
    data = content.encode("utf-8")
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def mesh():
    vertices, normals, uvs, faces = [], [], [], []
    for edge, (depth, radius) in enumerate(PROFILE):
        next_depth, next_radius = PROFILE[(edge + 1) % len(PROFILE)]
        dr, dz = next_radius - radius, next_depth - depth
        length = hypot(dr, dz)
        start = len(vertices)
        for ring, (end_depth, end_radius) in enumerate(((depth, radius), (next_depth, next_radius))):
            for segment in range(SEGMENTS):
                angle = tau * segment / SEGMENTS
                c, s = cos(angle), sin(angle)
                vertices.append((CENTER[0] + end_radius * c,
                                 CENTER[1] + end_radius * s, end_depth))
                normals.append((dz * c / length, dz * s / length, -dr / length))
                uvs.append((segment / SEGMENTS, ring))
        for segment in range(SEGMENTS):
            a = start + segment
            b = start + SEGMENTS + segment
            c = start + SEGMENTS + (segment + 1) % SEGMENTS
            d = start + (segment + 1) % SEGMENTS
            faces.extend(((a, c, b), (a, d, c)))

    welded = [tuple(round(x, 7) for x in v) for v in vertices]
    physical_edges = Counter()
    for face in faces:
        a, b, c = (vertices[i] for i in face)
        ab, ac = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        cross = (ab[1] * ac[2] - ab[2] * ac[1],
                 ab[2] * ac[0] - ab[0] * ac[2],
                 ab[0] * ac[1] - ab[1] * ac[0])
        assert sum(cross[i] * normals[face[0]][i] for i in range(3)) > 0
        for i in range(3):
            physical_edges[tuple(sorted((welded[face[i]], welded[face[(i + 1) % 3]])))] += 1
    assert set(physical_edges.values()) == {2}, "The inner sleeve must be a closed solid"

    lines = [f"mtllib {STEM}.mtl", "o marksman_baffle", "s 1"]
    for vertex, uv, normal in zip(vertices, uvs, normals):
        lines.append("v " + " ".join(f"{x:.8f}" for x in vertex))
        lines.append("vt " + " ".join(f"{x:.8f}" for x in uv))
        lines.append("vn " + " ".join(f"{x:.8f}" for x in normal))
    lines.append("usemtl marksman_baffle")
    for face in faces:
        lines.append("f " + " ".join(f"{i+1}/{i+1}/{i+1}" for i in face))
    write_changed(FOLDER / f"{STEM}_baffle.obj", "\n".join(lines) + "\n")
    return len(faces)


def main():
    triangles = mesh()
    write_changed(FOLDER / f"{STEM}_baffle.vmat", """Layer0
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "[0.004 0.005 0.006 1]"
    TextureRoughness "[0.96 0.96 0.96 1]"
    g_flMetalness "0"
}
""")

    mtl_path = FOLDER / f"{STEM}.mtl"
    mtl = mtl_path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in mtl else "\n"
    if "newmtl marksman_baffle" not in mtl:
        mtl += f"newmtl marksman_baffle{newline}Kd 1 1 1{newline}"
        write_changed(mtl_path, mtl)

    vmdl_path = FOLDER / f"{STEM}.vmdl"
    doc = vmdl_path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in doc else "\n"
    if 'from = "marksman_baffle.vmat"' not in doc:
        marker = " ] use_global_default = false"
        assert doc.count(marker) == 1
        remap = f', {{ from = "marksman_baffle.vmat" to = "{RESOURCE}/{STEM}_baffle.vmat" }}'
        doc = doc.replace(marker, remap + marker, 1)
    if 'name = "marksman_baffle"' not in doc:
        start = doc.index("[", doc.index('_class = "RenderMeshList"'))
        depth, end = 1, start + 1
        while depth:
            depth += (doc[end] == "[") - (doc[end] == "]")
            end += 1
        end -= 1
        node = (f'{{ _class = "RenderMeshFile" name = "marksman_baffle" '
                f'filename = "{RESOURCE}/{STEM}_baffle.obj" '
                'import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 '
                'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" } ')
        doc = doc[:end] + "," + newline + node + doc[end:]
    write_changed(vmdl_path, doc)
    print(f"Marksman ocular sleeve: {triangles} triangles; original model and lens geometry untouched.")


if __name__ == "__main__":
    main()
