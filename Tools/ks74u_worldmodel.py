"""Build the Kastov-74u third-person model from the MWII Kastovia Platform addon (workshop 3499492742).

The addon's w_akilo74 only holds the receiver; in GMod the barrel, mag, stock and grip are separate att_vm_*
models bone-merged onto its tag_*_attach bones. This merges the default 74u parts onto those tags into one
static mesh (the receiver's own selector lever is kept; the viewmodel-only "clamped1" copy is skipped).

Placement: the MW model space is tag_sling-relative (X forward, Y left, Z up, bore on y = 0.573). It is shifted
so the pistol grip lands where w_m4a1's grip is (area-weighted grip centroids: M4 -3.41,0,3.33; 74u
2.34,0.573,-2.65), so the citizen's hold_R pose fits it the same way.

Output is OBJ: this s&box build's ModelDoc no longer imports SMD ("Supported types: FBX, DMX, OBJ, VOX"). It reads
OBJ as Y-up: a test box spanning obj x 3, y 2, z 1 compiled to model x 1, y 3, z 2, so model (X, Y, Z) is written
as obj (Y, Z, X).

Also renders the buy-menu icon (ui/weapons/guns/kastov74u_01.png) from the same geometry.

Run: python Tools/ks74u_worldmodel.py (needs the Crowbar decompile under D:/tmp/hc1-mw22-tools/decompiled/akilo74)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kastov_smd import Smd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "Assets" / "Weapons" / "Kastov74u"
DECOMPILED = Path(r"D:/tmp/hc1-mw22-tools/decompiled/akilo74")

# tag_sling-relative positions of the attach bones (w_akilo74.qc $definebone; all unrotated).
TAGS = {
    None: (0.0, 0.0, 0.0),
    "tag_barrel_attach": (11.839, 0.573, 2.436),
    "tag_mag_attach": (9.487, 0.573, -0.094),
    "tag_stock_attach": (1.255, 0.573, 0.298),
    "tag_pistolgrip_attach": (3.971, 0.573, -0.351),
}

# (smd, tag its root bone merges onto)
PARTS = [
    ("w_akilo74/att_vm_p04_ar_akilo74_rec_v0_LOD0.smd", None),
    ("att_vm_p04_ar_akilo74_barrel_v0/att_vm_p04_ar_akilo74_barrel_v0_LOD0.smd", "tag_barrel_attach"),
    ("att_vm_p04_ar_akilo74_barrel_v0/att_vm_p04_ar_akilo74_barrel_v0_tip.smd", "tag_barrel_attach"),
    ("att_vm_p04_ar_akilo74_mag_v0/att_vm_p04_ar_akilo74_mag_v0_LOD0.smd", "tag_mag_attach"),
    ("att_vm_p04_ar_akilo74_stock_v0/att_vm_p04_ar_akilo74_stock_v0_LOD0.smd", "tag_stock_attach"),
    ("att_vm_p04_ar_akilo_pstlgrp_v0/att_vm_p04_ar_akilo_pstlgrp_v0_LOD0.smd", "tag_pistolgrip_attach"),
]

# MW tag_sling space -> HC1 world model space (grip matched to w_m4a1).
OFFSET = np.array([-5.75, -0.573, 6.0])

# MW-space points, reported in model space for the prefab.
POINTS = {
    "muzzle": (11.839 + 8.378, 0.573, 2.436 - 1.398),  # tag_barrel_attach + tag_flash_attachment
    "ejection_port": (9.103, -0.17, 1.884),  # tag_brass
    "optic": (3.745, 0.573, 2.958),  # tag_reflex
}

OBJ_NAME = "w_kastov74u.obj"
VMDL_NAME = "w_kastov74u.vmdl"

# Buy menu icon: white left-side silhouette on 1024x1024, at the M4 icon's scale (924px for its 31.1 units).
ICON = ROOT / "Assets" / "ui" / "weapons" / "guns" / "kastov74u_01.png"
ICON_PIXELS_PER_UNIT = 924 / 31.1


def to_model(points: np.ndarray) -> np.ndarray:
    return points + OFFSET


def to_obj(vectors: np.ndarray) -> np.ndarray:
    """Model space (X forward, Y left, Z up) -> the Y-up axes ModelDoc expects from OBJ."""
    return vectors[..., [1, 2, 0]]


def load_parts(materials: dict[str, str]):
    triangles = []
    for relative, tag in PARTS:
        smd = Smd(DECOMPILED / relative)
        shift = np.array(TAGS[tag])
        for material, vertices in smd.triangles:
            key = material.rsplit(".", 1)[0] if material.lower().endswith((".vmt", ".bmp", ".tga")) else material
            if key not in materials:
                raise KeyError(f"{relative}: no material mapping for {material}")
            stem = Path(materials[key]).stem
            triangles.append((stem, [(to_model(position + shift), normal, uv) for position, normal, uv, _ in vertices]))
    return triangles


def write_obj(path: Path, triangles) -> None:
    """One OBJ with shared (deduplicated) positions, UVs and normals, grouped by material."""
    corners = [(material, vertex) for material, vertices in triangles for vertex in vertices]
    positions = np.round(to_obj(np.array([v[0] for _, v in corners])), 5)
    normals = np.round(to_obj(np.array([v[1] for _, v in corners])), 4)
    uvs = np.round(np.array([v[2] for _, v in corners]), 5)
    unique_p, index_p = np.unique(positions, axis=0, return_inverse=True)
    unique_n, index_n = np.unique(normals, axis=0, return_inverse=True)
    unique_t, index_t = np.unique(uvs, axis=0, return_inverse=True)

    out = [f"mtllib {path.with_suffix('.mtl').name}", f"o {path.stem}"]
    out += [f"v {x:.5f} {y:.5f} {z:.5f}" for x, y, z in unique_p]
    out += [f"vt {u:.5f} {v:.5f}" for u, v in unique_t]
    out += [f"vn {x:.4f} {y:.4f} {z:.4f}" for x, y, z in unique_n]
    by_material: dict[str, list[int]] = {}
    for triangle, (material, _) in enumerate(triangles):
        by_material.setdefault(material, []).append(triangle)
    for material, members in by_material.items():
        out.append(f"usemtl {material}")
        for triangle in members:
            face = [3 * triangle + corner for corner in range(3)]
            out.append("f " + " ".join(f"{index_p[i] + 1}/{index_t[i] + 1}/{index_n[i] + 1}" for i in face))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    path.with_suffix(".mtl").write_text(
        "".join(f"newmtl {material}\nKd 1 1 1\n" for material in by_material), encoding="utf-8", newline="\n")


def write_icon(path: Path, triangles, size: int = 1024, supersample: int = 4) -> None:
    """Orthographic silhouette seen from the gun's left (muzzle pointing left), like the other HC1 gun icons."""
    from PIL import Image, ImageDraw

    points = np.array([[p for p, _, _ in vertices] for _, vertices in triangles])  # (tris, 3, xyz)
    u, v = -points[..., 0], points[..., 2]
    scale = ICON_PIXELS_PER_UNIT * supersample
    center_u = (u.min() + u.max()) / 2
    center_v = (v.min() + v.max()) / 2
    canvas = size * supersample
    px = (u - center_u) * scale + canvas / 2
    py = canvas / 2 - (v - center_v) * scale
    mask = Image.new("L", (canvas, canvas), 0)
    draw = ImageDraw.Draw(mask)
    for tri_x, tri_y in zip(px, py):
        draw.polygon(list(zip(tri_x, tri_y)), fill=255)
    alpha = mask.resize((size, size), Image.LANCZOS)
    icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    icon.putalpha(alpha)
    path.parent.mkdir(parents=True, exist_ok=True)
    icon.save(path)


def write_vmdl(path: Path, mesh_asset: str, stems: list[str], materials: dict[str, str]) -> None:
    by_stem = {Path(target).stem: target for target in materials.values()}
    remaps = "".join(
        "\t\t\t\t\t\t\t{\n"
        f'\t\t\t\t\t\t\t\tfrom = "{stem}.vmat"\n'
        f'\t\t\t\t\t\t\t\tto = "{by_stem[stem]}"\n'
        "\t\t\t\t\t\t\t},\n"
        for stem in stems)
    path.write_text(
        "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} "
        "format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
        "{\n"
        "\trootNode = \n"
        "\t{\n"
        '\t\t_class = "RootNode"\n'
        "\t\tchildren = \n"
        "\t\t[\n"
        "\t\t\t{\n"
        '\t\t\t\t_class = "MaterialGroupList"\n'
        "\t\t\t\tchildren = \n"
        "\t\t\t\t[\n"
        "\t\t\t\t\t{\n"
        '\t\t\t\t\t\t_class = "DefaultMaterialGroup"\n'
        "\t\t\t\t\t\tremaps = \n"
        "\t\t\t\t\t\t[\n"
        f"{remaps}"
        "\t\t\t\t\t\t]\n"
        "\t\t\t\t\t\tuse_global_default = false\n"
        '\t\t\t\t\t\tglobal_default_material = ""\n'
        "\t\t\t\t\t},\n"
        "\t\t\t\t]\n"
        "\t\t\t},\n"
        "\t\t\t{\n"
        '\t\t\t\t_class = "RenderMeshList"\n'
        "\t\t\t\tchildren = \n"
        "\t\t\t\t[\n"
        "\t\t\t\t\t{\n"
        '\t\t\t\t\t\t_class = "RenderMeshFile"\n'
        f'\t\t\t\t\t\tfilename = "{mesh_asset}"\n'
        "\t\t\t\t\t\timport_translation = [ 0.0, 0.0, 0.0 ]\n"
        "\t\t\t\t\t\timport_rotation = [ 0.0, 0.0, 0.0 ]\n"
        "\t\t\t\t\t\timport_scale = 1.0\n"
        '\t\t\t\t\t\talign_origin_x_type = "None"\n'
        '\t\t\t\t\t\talign_origin_y_type = "None"\n'
        '\t\t\t\t\t\talign_origin_z_type = "None"\n'
        '\t\t\t\t\t\tparent_bone = ""\n'
        "\t\t\t\t\t\timport_filter = \n"
        "\t\t\t\t\t\t{\n"
        "\t\t\t\t\t\t\texclude_by_default = false\n"
        "\t\t\t\t\t\t\texception_list = [  ]\n"
        "\t\t\t\t\t\t}\n"
        "\t\t\t\t\t},\n"
        "\t\t\t\t]\n"
        "\t\t\t},\n"
        "\t\t]\n"
        '\t\tmodel_archetype = ""\n'
        '\t\tprimary_associated_entity = ""\n'
        '\t\tanim_graph_name = ""\n'
        "\t}\n"
        "}\n",
        encoding="utf-8", newline="\n")


def main() -> None:
    manifest = json.loads((DEST / "ks74u_assets.json").read_text(encoding="utf-8"))
    materials = manifest["materials"]
    triangles = load_parts(materials)

    obj_path = DEST / "models" / OBJ_NAME
    write_obj(obj_path, triangles)
    stems = sorted({material for material, _ in triangles})
    obj_asset = obj_path.relative_to(ROOT / "Assets").as_posix().lower()
    write_vmdl(DEST / VMDL_NAME, obj_asset, stems, materials)
    write_icon(ICON, triangles)

    positions = np.array([p for _, vertices in triangles for p, _, _ in vertices])
    print(f"{len(triangles)} triangles, materials {stems}")
    print("bounds", positions.min(0).round(3), positions.max(0).round(3))
    for name, point in POINTS.items():
        print(name, to_model(np.array(point)).round(3))


if __name__ == "__main__":
    main()
