"""Riverdale's steel locker banks: two-tier lockers with formed doors, louvres, latches and hinges, replacing plain 20 in deep slabs.

python -X utf8 locker_bank.py            writes Assets/models/props/riverdale/locker_bank_v1/ (two models, three LODs each)

The old lockers were `box( m, e0, e1, n0, n1, z, z + 80, "rv_steel", METAL )`: one 12 triangle slab per bank, 52 or 80 in wide, 20 deep, 80 high
(B1's upper control room has two 80 in ones, each spawn building's upstairs room three 52 in ones). The slab's collision box stays in the map
models; the render is now a standalone model placed in the scene (Tools/riverdale_lockers.py), built inside the same 52/80 x 20 x 80 in envelope.

Built from the map's own materials (materials/riverdale/rv_*.vmat, nothing new): steel for the carcass and doors as before, dark for the plinth,
the gaps and the vent recesses, stainless for the latches, galvanised for the hinge barrels, white for the blank label cards. Plan axes as the
rest of the map: local e is the bank's width, local n its depth with the doors on +n, z up. In the engine +n is the model's forward (+x).
"""
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K  # noqa: E402
import riverdale_materials as RM  # noqa: E402
import riverdale_parts as G  # noqa: E402

OUT = ROOT / "Assets" / "models" / "props" / "riverdale" / "locker_bank_v1"
RESOURCE_DIR = "models/props/riverdale/locker_bank_v1"
MODELS = {"locker_bank_4": (52.0, 2), "locker_bank_6": (80.0, 3)}   # name: ( width, columns ), two tiers of doors in every column
LOD_THRESHOLDS = (0.0, 30.0, 80.0)

X = np.array((1.0, 0.0, 0.0))
Y = np.array((0.0, 1.0, 0.0))
Z = np.array((0.0, 0.0, 1.0))

DEPTH, HEIGHT = 20.0, 80.0
Y_BACK, Y_FRONT = -DEPTH / 2, DEPTH / 2
BASE_H = 4.5                # the recessed plinth
CAP_Z = 78.2                # the carcass's top; the cap is 1.8 thick above it
FACE = 8.7                  # the carcass's front plane
SLAB = (8.75, 9.55)         # a door's pressed pan: back and front
RIM = 10.0                  # the folded rim round it comes out to the envelope's front
DOOR_Z0, DOOR_Z1 = 5.2, 77.5
TIER_GAP = 0.6
SEAM = 0.7                  # between two doors side by side; the ends are 0.7 from the end returns
RETURN = 0.6                # end return width


def bx(m, c, size, paint, bevel=0.0, skip=(), axes=None):
    G.bevel_box(m, c, axes if axes is not None else (X, Y, Z), size, paint, bevel=bevel, skip=skip)


def post(m, x, y, z0, length, r, paint, sides, axis=Z):
    G.lathe_axis(m, (x, y, z0), axis, [(0, 0), (r, 0), (r, length), (0, length)], paint, sides=sides)


def door(m, x0, x1, z0, z1, upper, lod):
    """ One door, x0..x1 across and z0..z1 up, on the carcass's front. """
    w, h = x1 - x0, z1 - z0
    cx, zc = (x0 + x1) / 2, (z0 + z1) / 2
    ys = (SLAB[0] + SLAB[1]) / 2
    if lod >= 2:
        bx(m, (cx, ys + 0.5 * (RIM - SLAB[1]), zc), (w, RIM - SLAB[0], h), "rv_steel", 0.0)
        bx(m, (cx, RIM + 0.02, z1 - 5.4), (13.6, 0.04, 6.2), "rv_dark", 0.0, skip=("-y", "+x", "-x", "+z", "-z"))
        return
    # The pressed pan, and the folded rim round its edge that stands proud of it.
    bx(m, (cx, ys, zc), (w, SLAB[1] - SLAB[0], h), "rv_steel", 0.18)
    ry = (SLAB[1] + RIM) / 2
    rd = RIM - SLAB[1]
    r = 1.05
    skip = ("-y",)
    bx(m, (cx, ry, z1 - r / 2), (w, rd, r), "rv_steel", 0.0, skip)
    bx(m, (cx, ry, z0 + r / 2), (w, rd, r), "rv_steel", 0.0, skip)
    for side in (-1, 1):
        bx(m, (cx + side * (w / 2 - r / 2), ry, zc), (r, rd, h - 2 * r), "rv_steel", 0.0, skip + ("+z", "-z"))
    # The vent bank near the top: a dark recess with angled blades between two posts.
    vz = z1 - 5.2
    bx(m, (cx, SLAB[1] + 0.04, vz), (13.6, 0.08, 6.3), "rv_dark", 0.0, skip=("-y", "+x", "-x", "+z", "-z"))
    count, pitch = (5, 1.12) if lod == 0 else (3, 1.9)
    a = math.radians(20.0)
    out = Y * math.cos(a) + Z * math.sin(a)
    up = -Y * math.sin(a) + Z * math.cos(a)
    for j in range(count):
        bx(m, (cx, 9.78, vz + (j - (count - 1) / 2) * pitch), (12.9, 0.42, 0.30), "rv_steel", 0.0, axes=(X, out, up))
    for side in (-1, 1):
        bx(m, (cx + side * 6.9, 9.78, vz), (0.30, 0.46, 6.3), "rv_steel", 0.0, skip=("-y",))
    # The latch: a recessed pocket with a stainless lift bar and, at full detail, its two studs and a key barrel.
    lx = x1 - 3.4
    lz = z0 + h * (0.45 if upper else 0.62)
    bx(m, (lx, SLAB[1] + 0.04, lz), (2.6, 0.08, 5.6), "rv_dark", 0.0, skip=("-y", "+x", "-x", "+z", "-z"))
    bx(m, (lx, 9.86, lz), (0.9, 0.5, 4.0), "rv_stainless", 0.14 if lod == 0 else 0.0, skip=("-y",))
    if lod == 0:
        for dz in (-1.9, 1.9):
            post(m, lx, SLAB[1], lz + dz, 0.36, 0.28, "rv_stainless", 8, axis=Y)
        post(m, lx, SLAB[1], lz + 3.7, 0.30, 0.38, "rv_stainless", 10, axis=Y)
        bx(m, (lx, 9.88, lz + 3.7), (0.09, 0.02, 0.5), "rv_dark", 0.0, skip=("-y", "+x", "-x", "+z", "-z"))
        # Hinge barrels in the seam, a blank label holder on the pan.
        for dz in (-0.3 * h, 0.3 * h):
            post(m, x0 - 0.02, 9.2, zc + dz - 1.5, 3.0, 0.30, "rv_galv", 8)
        bx(m, (x0 + 3.35, 9.62, z1 - 5.2), (3.4, 0.14, 1.9), "rv_dark", 0.0, skip=("-y",))
        bx(m, (x0 + 3.35, 9.71, z1 - 5.2), (3.0, 0.06, 1.5), "rv_white", 0.0, skip=("-y",))


def build(width, columns, lod=0):
    m = K.Model()
    half = width / 2
    cw = width / columns
    hx = half - 0.02
    # Plinth, carcass, top cap and the end returns.
    plinth_y0, plinth_y1 = Y_BACK + 0.7, 8.4          # recessed 1.3 in from the doors and 0.7 in from the back
    bx(m, (0, (plinth_y0 + plinth_y1) / 2, (BASE_H + 0.1) / 2), (width - 1.4, plinth_y1 - plinth_y0, BASE_H + 0.1), "rv_dark", 0.12 if lod < 2 else 0.0)
    carcass_y0, carcass_y1 = Y_BACK, FACE
    bx(m, (0, (carcass_y0 + carcass_y1) / 2, (BASE_H + CAP_Z) / 2), (2 * hx, carcass_y1 - carcass_y0, CAP_Z - BASE_H), "rv_steel", 0.22 if lod < 2 else 0.0)
    bx(m, (0, 0, CAP_Z + (HEIGHT - CAP_Z) / 2), (width, DEPTH, HEIGHT - CAP_Z), "rv_steel", 0.35 if lod < 2 else 0.0)
    # The dark liner the gaps between doors show.
    bx(m, (0, (FACE + SLAB[0]) / 2 - 0.02, (DOOR_Z0 + DOOR_Z1) / 2 - 0.2), (width - 1.0, SLAB[0] - FACE + 0.06, DOOR_Z1 - DOOR_Z0 + 0.8), "rv_dark", 0.0, skip=("-y", "+x", "-x", "+z", "-z"))
    for side in (-1, 1):
        bx(m, (side * (half - RETURN / 2 - 0.02), (8.6 + RIM) / 2, (BASE_H + CAP_Z) / 2), (RETURN, RIM - 8.6, CAP_Z - BASE_H), "rv_steel", 0.12 if lod < 2 else 0.0, skip=("-y",))
    dh = (DOOR_Z1 - DOOR_Z0 - TIER_GAP) / 2
    for c in range(columns):
        x0 = -half + c * cw + (SEAM if c == 0 else SEAM / 2)
        x1 = -half + (c + 1) * cw - (SEAM if c == columns - 1 else SEAM / 2)
        door(m, x0, x1, DOOR_Z0, DOOR_Z0 + dh, False, lod)
        door(m, x0, x1, DOOR_Z0 + dh + TIER_GAP, DOOR_Z1, True, lod)
    for paint in m.polygons:
        m.material_overrides[paint] = f"{RM.RESOURCE_DIR}/{paint}.vmat"
        m.tile_overrides[paint] = RM.TILES.get(paint, 64.0)
    return m


def vmdl_text(name, paints):
    remaps = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{RM.RESOURCE_DIR}/{p}.vmat" }}' for p in sorted(paints))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{RESOURCE_DIR}/{name}_lod{k}.obj" import_translation = [ 0.0, 0.0, 0.0 ] '
        'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] } }'
        for k in range(3))
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{k}" ] }}' for k, t in enumerate(LOD_THRESHOLDS))
    return ("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
            "// Generated by Sources/Riverdale/locker-bank-v1/locker_bank.py\n"
            "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
            "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n"
            "\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n" + remaps + "\n\t\t\t\t\t\t]\n"
            "\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + groups + "\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n")


def write_all(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, (width, columns) in MODELS.items():
        paints = set()
        tris = []
        for lod in range(3):
            model = build(width, columns, lod)
            model.uv_source_name = name           # one UV origin for every LOD, so a switch never shifts the textures
            tris.append(K.write_obj(out / f"{name}_lod{lod}.obj", model, name))
            paints |= set(model.polygons)
        K.write_text(out / f"{name}.vmdl", vmdl_text(name, paints))
        report[name] = tris
    return report


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    for name, tris in write_all(target).items():
        print(name, "triangles by LOD", tris, "->", target)
