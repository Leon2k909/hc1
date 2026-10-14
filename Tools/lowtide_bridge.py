"""Lowtide footbridge: generated weathered timber, full-width boards and matching surface maps."""

import argparse
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import find_peaks

import map_kit as K

SOURCE = K.ROOT / "Tools/lowtide_bridge_source.png"
DIRECTORY = K.ASSETS / "materials/lowtide"
RESOURCE = "materials/lowtide/lt_bridge_deck"
PAINT = "lt_bridge_deck"
BOARD_WIDTH = 6.0
TILE_UNITS = 96.0


def metadata(path):
    sidecar = Path(str(path) + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid4())}, indent=2) + "\n")


def atlas_layout():
    image = np.asarray(Image.open(SOURCE).convert("RGB"))
    height, width = image.shape[:2]
    luminance = image.astype(float).mean(axis=2) / 255
    seams, _ = find_peaks(-luminance[:, width // 12:-width // 12].mean(axis=1),
                          distance=height / 28, prominence=.05)
    seams = seams[(seams > height * .035) & (seams < height * .965)]
    rows = [(int(a), int(b)) for a, b in zip(seams[:-1], seams[1:])
            if height / 25 < b - a < height / 8]
    if len(rows) < 8:
        raise ValueError("The timber source must contain at least eight uninterrupted horizontal boards")
    atlas = 1 << int(np.ceil(np.log2(max(height, width))))
    return image, rows, atlas


def bake_surface_maps():
    image, rows, atlas = atlas_layout()
    luminance = image.astype(float) @ np.array([.2126, .7152, .0722]) / 255
    grain = luminance - ndimage.gaussian_filter(luminance, (1.0, 6.0))
    # Millimetre-scale checking rather than inflating the photographic grain into deep grooves.
    height = np.clip(grain, -.2, .2) * .055
    seam_distance = np.full(image.shape[0], np.inf)
    for a, b in rows:
        seam_distance = np.minimum(seam_distance, np.minimum(abs(np.arange(image.shape[0]) - a),
                                                            abs(np.arange(image.shape[0]) - b)))
    joint = np.exp(-np.square(seam_distance / 1.5))[:, None]
    height -= joint * .040
    pixel_u = 108.0 / (image.shape[1] - 1)
    pixel_v = BOARD_WIDTH / np.median([b - a for a, b in rows])
    dy, dx = np.gradient(height)
    normal = np.stack((-dx / pixel_u, dy / pixel_v, np.ones_like(height)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    roughness = np.clip(.87 + grain * .18 + joint * .05, .78, .96)
    ao = np.broadcast_to(1 - joint * .22, luminance.shape)
    maps = {
        "color": image,
        "normal": np.rint((normal + 1) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255).astype(np.uint8),
        "ao": np.rint(ao * 255).astype(np.uint8),
    }
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for suffix, pixels in maps.items():
        padding = [(0, atlas - pixels.shape[0]), (0, atlas - pixels.shape[1])]
        if pixels.ndim == 3:
            padding.append((0, 0))
        # Technical POT atlas packing: all original albedo pixels remain byte-for-byte unchanged.
        packed = np.pad(pixels, padding, mode="edge")
        path = DIRECTORY / f"{PAINT}_{suffix}.png"
        Image.fromarray(packed).save(path, optimize=True)
        metadata(path)
    return rows, atlas


def write_materials():
    if not (DIRECTORY / f"{PAINT}_color.png").exists():
        bake_surface_maps()
    path = DIRECTORY / f"{PAINT}.vmat"
    K.write_text(path, f'''// Tools/lowtide_bridge.py: weathered timber with individually mapped full-width boards.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "{RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness "{RESOURCE}_rough.png"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1"
}}
''')
    metadata(path)


def configure(model):
    if PAINT in model.polygons:
        model.material_overrides[PAINT] = f"{RESOURCE}.vmat"
        model.tile_overrides[PAINT] = TILE_UNITS


def deck_surface(model, e0, e1, n0, n1, z=0):
    """Six-inch transverse boards; independent atlas rows eliminate repeating tile/end-joint patterns."""
    image, rows, atlas = atlas_layout()
    rng = np.random.default_rng(8137)
    count = int(np.ceil((e1 - e0) / BOARD_WIDTH))
    order = []
    while len(order) < count:
        batch = list(rng.permutation(len(rows)))
        if order and order[-1] == batch[0]:
            batch = batch[1:] + batch[:1]
        order.extend(batch)
    for k in range(count):
        a, b = rows[order[k]]
        u0, u1 = .5 / atlas, (image.shape[1] - .5) / atlas
        # OBJ import flips V. Compensate here so every board samples its actual
        # scanned row rather than the edge-padded bottom half of the atlas.
        v0, v1 = 1 - (a + .5) / atlas, 1 - (b + .5) / atlas
        if rng.random() < .5:
            u0, u1 = u1, u0
        if rng.random() < .5:
            v0, v1 = v1, v0
        left, right = e0 + k * BOARD_WIDTH, min(e0 + (k + 1) * BOARD_WIDTH, e1)
        points = [(left, n0, z), (right, n0, z), (right, n1, z), (left, n1, z)]
        model.polygon(PAINT, points, normal=(0, 0, 1), uv=[(u0, v0), (u0, v1), (u1, v1), (u1, v0)])


def patch_existing_bridge():
    """Replace only the existing deck's two draw triangles; preserve every other face and all collision shapes."""
    import lowtide_map as low

    directory = K.ASSETS / "models/maps/lowtide"
    path = directory / "lowtide_fleet.obj"
    lines = path.read_text(encoding="utf-8").splitlines()
    if f"usemtl {PAINT}" in lines:
        return
    vertices = [tuple(map(float, line.split()[1:])) for line in lines if line.startswith("v ")]
    uv_count = sum(line.startswith("vt ") for line in lines)
    n0, n1 = low.FOOTBRIDGE[0] + 6, low.FOOTBRIDGE[1] - 6
    material, targets = "", []
    for index, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        if material != "planks" or not line.startswith("f "):
            continue
        points = [vertices[int(token.split("/")[0]) - 1] for token in line.split()[1:]]
        if all(abs(p[1]) < 1e-6 and -low.FLEET <= p[0] <= low.FLEET and n0 <= p[2] <= n1 for p in points):
            targets.append(index)
    if len(targets) != 2 or targets[1] != targets[0] + 1:
        raise ValueError(f"Expected exactly the two existing bridge floor triangles, found {targets}")
    old_normal = lines[targets[0]].split()[1].split("/")[2]
    deck = K.Model()
    deck_surface(deck, -low.FLEET, low.FLEET, n0, n1)
    additions, new_faces = [], [f"usemtl {PAINT}"]
    vertex_count = len(vertices)
    for index, (points, normal) in enumerate(deck.polygons[PAINT]):
        coords = deck.polygon_uvs[(PAINT, index)]
        tokens = []
        for point, (u, v) in zip(points, coords):
            vertex_count += 1
            uv_count += 1
            additions.append(f"v {K.obj_vector(K.to_world(point))}")
            additions.append(f"vt {u:.5f} {v:.5f}")
            tokens.append(f"{vertex_count}/{uv_count}/{old_normal}")
        new_faces.extend((f"f {tokens[0]} {tokens[1]} {tokens[2]}", f"f {tokens[0]} {tokens[2]} {tokens[3]}"))
    new_faces.append("usemtl planks")
    split = next(i for i, line in enumerate(lines) if line.startswith("usemtl "))
    updated = lines[:split] + additions
    for index in range(split, len(lines)):
        if index == targets[0]:
            updated.extend(new_faces)
        elif index != targets[1]:
            updated.append(lines[index])
    K.write_text(path, "\n".join(updated) + "\n")
    mtl = path.with_suffix(".mtl")
    K.write_text(mtl, mtl.read_text() + f"newmtl {PAINT}\nKd 1 1 1\nd 1\n")
    vmdl = path.with_suffix(".vmdl")
    text = vmdl.read_text()
    pattern = r'(?m)^([ \t]*)\{ from = "planks\.vmat" to = "materials/buildings/planks\.vmat" \},?$'
    match = re.search(pattern, text)
    if not match:
        raise ValueError("Missing original plank material remap in the Fleet model")
    remap = f'\n{match.group(1)}{{ from = "{PAINT}.vmat" to = "{RESOURCE}.vmat" }},'
    K.write_text(vmdl, text[:match.end()] + remap + text[match.end():])
    print(f"Updated only the bridge floor: {len(deck.polygons[PAINT])} full-width boards")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="copy a generated timber source unchanged")
    args = parser.parse_args()
    if args.source and args.source.resolve() != SOURCE.resolve():
        shutil.copy2(args.source, SOURCE)
    rows, atlas = bake_surface_maps()
    write_materials()
    patch_existing_bridge()
    print(f"{len(rows)} scanned boards, {atlas}-pixel POT atlas; source {hashlib.sha256(SOURCE.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
