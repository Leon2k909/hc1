"""Riverdale B1's control-room desk: a steel workstation desk with a drawer pedestal, kneehole, modesty panel and cable tray, replacing a plain 72 x 40 x 30 in box.

python -X utf8 desk.py            writes Assets/models/props/riverdale/b1_desk_v1/ (b1_desk.vmdl, three LODs)

The old desk was `box( m, -36, 36, -960, -920, ROOM_Z, ROOM_Z + 30, { "default": "rv_desk", "+z": "rv_dark" }, METAL )`: 12 triangles. Its collision box stays in the map model;
this model is built in the same 72 x 40 x 30 in envelope. Only the map's own materials (rv_desk, rv_dark, rv_stainless, rv_steel, rv_galv, rv_white). Plan axes: local x is the desk's
width (east), local y its depth with the user's side (drawers, kneehole) on +y (north), z up.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K  # noqa: E402
import riverdale_materials as RM  # noqa: E402
import riverdale_parts as G  # noqa: E402

OUT = ROOT / "Assets" / "models" / "props" / "riverdale" / "b1_desk_v1"
RESOURCE_DIR = "models/props/riverdale/b1_desk_v1"
NAME = "b1_desk"
LOD_THRESHOLDS = (0.0, 30.0, 80.0)
X = np.array((1.0, 0.0, 0.0))
Y = np.array((0.0, 1.0, 0.0))
Z = np.array((0.0, 0.0, 1.0))
W, D, H = 72.0, 40.0, 30.0
TOP_Z0 = 28.4          # the top's underside; it is 1.6 thick
PED_W = 17.0           # the drawer pedestal's width
PANEL = 1.2            # end panel and modesty panel thickness


def bx(m, c, size, paint, bevel=0.0, skip=(), axes=None):
    G.bevel_box(m, c, axes if axes is not None else (X, Y, Z), size, paint, bevel=bevel, skip=skip)


def post(m, x, y, z0, length, r, paint, sides, axis=Z):
    G.lathe_axis(m, (x, y, z0), axis, [(0, 0), (r, 0), (r, length), (0, length)], paint, sides=sides)


def build(lod=0):
    m = K.Model()
    fine = lod < 2
    bev = lambda b: b if fine else 0.0  # noqa: E731
    # The top: a 1.6 in laminate slab with eased edges, and a steel edge band along the user's side.
    bx(m, (0, 0, TOP_Z0 + 0.8), (W, D, 1.6), "rv_dark", bev(0.35))
    if lod == 0:
        bx(m, (0, D / 2 - 0.15, TOP_Z0 + 0.8), (W - 0.8, 0.3, 1.62), "rv_steel", 0.0, skip=("-y",))
    # Drawer pedestal (left), end panel (right), modesty panel behind the kneehole, plinths.
    x0 = -W / 2 + 0.8
    ped_y0, ped_y1 = -D / 2 + 0.8, D / 2 - 1.0
    ped_x1 = x0 + PED_W
    bx(m, ((x0 + ped_x1) / 2, (ped_y0 + ped_y1) / 2, 3.0 + (TOP_Z0 - 3.0) / 2), (PED_W, ped_y1 - ped_y0, TOP_Z0 - 3.0), "rv_desk", bev(0.2))
    bx(m, ((x0 + ped_x1) / 2 + 0.2, (ped_y0 + ped_y1) / 2 - 0.3, 1.5), (PED_W - 1.0, ped_y1 - ped_y0 - 0.6, 3.0), "rv_dark", bev(0.1))
    ex1 = W / 2 - 0.8
    bx(m, (ex1 - PANEL / 2, (ped_y0 + ped_y1) / 2, 3.0 + (TOP_Z0 - 3.0) / 2), (PANEL, ped_y1 - ped_y0, TOP_Z0 - 3.0), "rv_desk", bev(0.15))
    bx(m, (ex1 - PANEL / 2 - 0.2, (ped_y0 + ped_y1) / 2 - 0.3, 1.5), (PANEL + 0.4, ped_y1 - ped_y0 - 0.6, 3.0), "rv_dark", bev(0.1))
    mx0, mx1 = ped_x1, ex1 - PANEL
    bx(m, ((mx0 + mx1) / 2, ped_y0 + PANEL / 2, 8.0 + (TOP_Z0 - 8.0) / 2), (mx1 - mx0, PANEL, TOP_Z0 - 8.0), "rv_desk", bev(0.15))
    # Drawer fronts on the pedestal's user side: three, each with a handle, a label holder and (top one) a lock.
    fy = ped_y1
    gap = 0.5
    dh = (TOP_Z0 - 3.4 - gap * 2) / 3
    bx(m, ((x0 + ped_x1) / 2, fy + 0.02, 3.0 + (TOP_Z0 - 3.0) / 2), (PED_W - 0.6, 0.04, TOP_Z0 - 3.4), "rv_dark", 0.0, skip=("-y", "+x", "-x", "+z", "-z"))
    for k in range(3):
        z0 = 3.4 + k * (dh + gap)
        zc = z0 + dh / 2
        cx = (x0 + ped_x1) / 2
        bx(m, (cx, fy + 0.3, zc), (PED_W - 1.2, 0.6, dh), "rv_desk", bev(0.16))
        if lod == 0:
            bx(m, (cx, fy + 0.62, z0 + dh - 1.4), (3.4, 0.06, 1.1), "rv_dark", 0.0, skip=("-y",))
            bx(m, (cx, fy + 0.66, z0 + dh - 1.4), (3.0, 0.04, 0.8), "rv_white", 0.0, skip=("-y",))
            for s in (-1, 1):
                post(m, cx + s * 2.6, fy + 0.6, zc - 0.9, 0.9, 0.32, "rv_stainless", 8, axis=Y)
            bx(m, (cx, fy + 1.62, zc - 0.9), (6.8, 0.6, 0.7), "rv_stainless", 0.14)
        elif lod == 1:
            bx(m, (cx, fy + 1.5, zc - 0.9), (6.8, 0.8, 0.7), "rv_stainless", 0.0)
    if lod == 0:
        post(m, x0 + PED_W - 3.2, fy + 0.6, 3.4 + 2 * (dh + gap) + dh - 3.2, 0.3, 0.45, "rv_stainless", 10, axis=Y)
        # Cable tray under the top behind the kneehole, a grommet in the top, levelling feet.
        bx(m, ((mx0 + mx1) / 2, -D / 2 + 6.5, TOP_Z0 - 1.4), (mx1 - mx0 - 4.0, 8.0, 2.2), "rv_dark", 0.12)
        bx(m, (22.0, -D / 2 + 7.0, H + 0.03), (3.2, 3.2, 0.06), "rv_dark", 0.0, skip=("-z", "+x", "-x", "+y", "-y"))
        for fx in (x0 + 1.4, ex1 - 1.4):
            for fyy in (ped_y0 + 1.4, ped_y1 - 1.4):
                post(m, fx, fyy, 0.0, 0.5, 0.7, "rv_galv", 8)
    for paint in m.polygons:
        m.material_overrides[paint] = f"{RM.RESOURCE_DIR}/{paint}.vmat"
        m.tile_overrides[paint] = RM.TILES.get(paint, 64.0)
    return m


def vmdl_text(paints):
    remaps = ",\n".join(f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{RM.RESOURCE_DIR}/{p}.vmat" }}' for p in sorted(paints))
    meshes = ",\n".join(
        f'\t\t\t\t\t{{ _class = "RenderMeshFile" name = "lod{k}" filename = "{RESOURCE_DIR}/{NAME}_lod{k}.obj" import_translation = [ 0.0, 0.0, 0.0 ] '
        'import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" parent_bone = "" import_filter = { exclude_by_default = false exception_list = [ ] } }'
        for k in range(3))
    groups = ",\n".join(f'\t\t\t\t\t{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = [ "lod{k}" ] }}' for k, t in enumerate(LOD_THRESHOLDS))
    return ("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n"
            "// Generated by Sources/Riverdale/b1-desk-v1/desk.py\n"
            "{\n\trootNode =\n\t{\n\t\t_class = \"RootNode\"\n\t\tchildren =\n\t\t[\n"
            "\t\t\t{\n\t\t\t\t_class = \"MaterialGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n\t\t\t\t\t{\n\t\t\t\t\t\t_class = \"DefaultMaterialGroup\"\n"
            "\t\t\t\t\t\tremaps =\n\t\t\t\t\t\t[\n" + remaps + "\n\t\t\t\t\t\t]\n"
            "\t\t\t\t\t\tuse_global_default = false\n\t\t\t\t\t\tglobal_default_material = \"\"\n\t\t\t\t\t},\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"RenderMeshList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + meshes + "\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t\t{\n\t\t\t\t_class = \"LODGroupList\"\n\t\t\t\tchildren =\n\t\t\t\t[\n" + groups + "\n\t\t\t\t]\n\t\t\t},\n"
            "\t\t]\n\t\tmodel_archetype = \"\"\n\t\tprimary_associated_entity = \"\"\n\t\tanim_graph_name = \"\"\n\t\tbase_model_name = \"\"\n\t}\n}\n")


def write_all(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    paints, tris = set(), []
    for lod in range(3):
        model = build(lod)
        model.uv_source_name = NAME
        tris.append(K.write_obj(out / f"{NAME}_lod{lod}.obj", model, NAME))
        paints |= set(model.polygons)
    K.write_text(out / f"{NAME}.vmdl", vmdl_text(paints))
    return tris


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    print(NAME, "triangles by LOD", write_all(target), "->", target)
