"""View-dependent interiors for sealed Lowtide windows; no geometry or physics edits.

stage() prepares only UV changes for the existing rw_window_dark polygons in the
east, west and backdrop architecture. Apply staged files through the editor.
Crane glazing, dressing models and playable transparent windows are excluded.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import shutil
from pathlib import Path
import zlib

import numpy as np
from PIL import Image

import map_kit as K
from lowtide_brick import metadata

PAINT = "rw_window_dark"
NAMES = ("lowtide_east", "lowtide_west", "lowtide_backdrop")
MATERIAL = "materials/lowtide/windows/lt_window_interior.vmat"
SOURCE = K.ROOT / "Sources/Lowtide/visual-target/warehouse-room-atlas.png"
FOLDER = K.ASSETS / "materials/lowtide/windows"
STAGE = K.ROOT / "output/lowtide/quality-pass/window-stage"


def bake(source):
    FOLDER.mkdir(parents=True, exist_ok=True)
    if Path(source).resolve() != SOURCE.resolve():
        shutil.copy2(source, SOURCE)
    path = FOLDER / "warehouse_rooms.png"
    Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS).save(path)
    metadata(path)


def write_materials():
    if not (FOLDER / "warehouse_rooms.png").exists():
        raise FileNotFoundError("Bake the generated warehouse room atlas first")
    path = K.ASSETS / MATERIAL
    K.write_text(path, '''// Tools/lowtide_windows.py: sealed building windows only.
"Layer0"
{
    shader "shaders/hc1_lowtide_window_interior.shader"
    TextureColor "[0.015 0.021 0.020 0]"
    TextureNormal "materials/railhead/window_dark_normal.png"
    TextureRoughness "materials/railhead/window_dark_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    TextureRoomBack "materials/lowtide/windows/warehouse_rooms.png"
    TextureRoomWall "materials/lowtide/lt_plaster_color.png"
    TextureRoomWood "materials/lowtide/interior/ceiling_color.png"
    g_flInteriorBrightness "0.16"
    g_flRoomDepth "32"
}
''')
    metadata(path)
    metadata(K.ASSETS / "shaders/hc1_lowtide_window_interior.shader")


def coordinates(world, normal):
    world, normal = np.asarray(world), np.asarray(normal)
    right = np.cross((0, 0, 1), normal)
    right /= np.linalg.norm(right)
    horizontal = world @ right
    vertical = world[:, 2]
    width, height = np.ptp(horizontal), np.ptp(vertical)
    if width < .1 or height < .1:
        raise ValueError("Degenerate sealed window")
    centre = (world.min(axis=0) + world.max(axis=0)) * .5
    key = ",".join(f"{x:.2f}" for x in np.r_[centre, normal])
    variant = zlib.crc32(key.encode()) % 4
    return [(variant*2 + .001 + .998*(u-horizontal.min())/width,
             .001 + .998*(v-vertical.min())/height) for u, v in zip(horizontal, vertical)]


def configure(model):
    if PAINT not in model.polygons:
        return
    model.material_overrides[PAINT] = MATERIAL
    for i, (points, normal) in enumerate(model.polygons[PAINT]):
        model.polygon_uvs[(PAINT, i)] = coordinates([K.to_world(p) for p in points], K.to_world(normal))


def prepare_obj(path):
    original = path.read_bytes()
    lines = original.decode().splitlines()
    vertices, normals, uv_lines = [], [], []
    groups = defaultdict(set)
    other_uvs = set()
    active = False
    for row, line in enumerate(lines):
        if line.startswith("v "):
            xyz = [float(x) for x in line.split()[1:]]
            vertices.append(np.array((xyz[2], xyz[0], xyz[1])))
        elif line.startswith("vn "):
            xyz = [float(x) for x in line.split()[1:]]
            normals.append(np.array((xyz[2], xyz[0], xyz[1])))
        elif line.startswith("vt "):
            uv_lines.append(row)
        elif line.startswith("usemtl "):
            active = line.split(maxsplit=1)[1] == PAINT
        elif line.startswith("f "):
            refs = [tuple(int(x) for x in part.split("/")) for part in line.split()[1:]]
            if active:
                assert len({r[2] for r in refs}) == 1, "Expected a planar window polygon"
                groups[refs[0][2]].update((v, t) for v, t, _ in refs)
            else:
                other_uvs.update(t for _, t, _ in refs)
    changed_rows = set()
    for normal_id, refs in groups.items():
        refs = sorted(refs)
        assert not {t for _, t in refs} & other_uvs, "UV shared with non-window geometry"
        uv = coordinates([vertices[v-1] for v, _ in refs], normals[normal_id-1])
        for (_, t), (u, v) in zip(refs, uv):
            row = uv_lines[t-1]
            lines[row] = f"vt {u:.5f} {v:.5f}"
            changed_rows.add(row)
    assert groups
    newline = "\r\n" if b"\r\n" in original else "\n"
    updated = (newline.join(lines) + newline).encode()
    old_lines = original.decode().splitlines()
    assert all(a == b or i in changed_rows for i, (a, b) in enumerate(zip(old_lines, lines)))
    assert len(old_lines) == len(lines)
    return updated, {"windows": len(groups), "uv_count": len(changed_rows),
                     "sha256": hashlib.sha256(original).hexdigest()}


def stage():
    STAGE.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in NAMES:
        path = K.ASSETS / f"models/maps/lowtide/{name}.obj"
        updated, info = prepare_obj(path)
        (STAGE / path.name).write_bytes(updated)
        manifest[name] = info
    (STAGE / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--stage", action="store_true")
    args = parser.parse_args()
    if args.source:
        bake(args.source)
    write_materials()
    if args.stage:
        stage()
