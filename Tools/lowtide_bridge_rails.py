"""Weathered steel for Lowtide's bridge, with scale-correct scan detail and face-aligned edge wear."""

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

import map_kit as K

SOURCE = K.ROOT / "Tools/lowtide_bridge_steel_source.png"
DIRECTORY = K.ASSETS / "materials/lowtide"
PAINT = "lt_bridge_steel"
RESOURCE = f"materials/lowtide/{PAINT}"
SHADER = K.ASSETS / "shaders/hc1_bridge_steel.shader"
TILE_UNITS = 24.0


def metadata(path):
    sidecar = Path(str(path) + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid4())}, indent=2) + "\n")


def atlas_layout():
    image = np.asarray(Image.open(SOURCE).convert("RGB"))
    atlas = 1 << int(np.ceil(np.log2(max(image.shape[:2]))))
    return image, atlas


def bake_surface_maps():
    image, atlas = atlas_layout()
    rgb = image.astype(float) / 255
    r, g, b = np.moveaxis(rgb, -1, 0)
    luminance = rgb @ np.array([.2126, .7152, .0722])
    rust = np.clip((r - (g + b) * .5 - .025) * 8, 0, 1)
    rust = ndimage.gaussian_filter(rust, .7)
    chips = np.clip((luminance - ndimage.gaussian_filter(luminance, 5) - .025) * 10, 0, 1) * (1 - rust)
    fine = luminance - ndimage.gaussian_filter(luminance, 1.5)
    # Paint texture and corrosion are fractions of a millimetre deep, not stone-like bumps.
    height = fine * .008 - chips * .004 + rust * .003
    dy, dx = np.gradient(height)
    pixel_u = TILE_UNITS / (image.shape[1] - 1)
    pixel_v = TILE_UNITS / (image.shape[0] - 1)
    normal = np.stack((-dx / pixel_u, dy / pixel_v, np.ones_like(height)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    maps = {
        "color": image,
        "normal": np.rint((normal + 1) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(np.clip(.73 + rust * .17 - chips * .27, .43, .95) * 255).astype(np.uint8),
        "metal": np.rint(np.clip(.02 + chips * .86 - rust * .02, 0, .9) * 255).astype(np.uint8),
        "ao": np.rint((1 - rust * .06 - chips * .04) * 255).astype(np.uint8),
    }
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    for suffix, pixels in maps.items():
        padding = [(0, atlas - pixels.shape[0]), (0, atlas - pixels.shape[1])]
        if pixels.ndim == 3:
            padding.append((0, 0))
        # POT packing preserves the generated albedo exactly; the shader samples only the original scan region.
        path = DIRECTORY / f"{PAINT}_{suffix}.png"
        Image.fromarray(np.pad(pixels, padding, mode="edge")).save(path, optimize=True)
        metadata(path)


def write_materials():
    if not (DIRECTORY / f"{PAINT}_color.png").exists():
        bake_surface_maps()
    image, atlas = atlas_layout()
    u0, v0 = .5 / atlas, .5 / atlas
    du, dv = (image.shape[1] - 1) / atlas, (image.shape[0] - 1) / atlas
    path = DIRECTORY / f"{PAINT}.vmat"
    K.write_text(path, f'''// Tools/lowtide_bridge_rails.py: photographic painted steel with physical edge wear.
"Layer0"
{{
    shader "shaders/hc1_bridge_steel.shader"
    F_SPECULAR "1"
    TextureColor "{RESOURCE}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness "{RESOURCE}_rough.png"
    TextureMetalness "{RESOURCE}_metal.png"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    g_flTintColor "[1.0 1.0 1.0]"
    g_vSteelRegion "[{u0:.9f} {v0:.9f} {du:.9f} {dv:.9f}]"
    g_flSteelTile "24"
    g_flEdgeWearWidth "0.11"
}}
''')
    metadata(path)
    metadata(SHADER)


def finish_bridge(model, first_steel):
    """Move just the bridge's steel faces to the dedicated material and give each rectangle normalized UVs."""
    pieces = model.polygons["lt_steel"][first_steel:]
    model.polygons["lt_steel"] = model.polygons["lt_steel"][:first_steel]
    for points, normal in pieces:
        if len(points) != 4:
            raise ValueError("Bridge edge wear requires rectangular steel faces")
        model.polygon(PAINT, points, normal=normal, uv=[(0, 0), (1, 0), (1, 1), (0, 1)])


def configure(model):
    if PAINT in model.polygons:
        model.material_overrides[PAINT] = f"{RESOURCE}.vmat"
        model.tile_overrides[PAINT] = TILE_UNITS


def patch_existing_bridge():
    import lowtide_map as low

    path = K.ASSETS / "models/maps/lowtide/lowtide_fleet.obj"
    lines = path.read_text(encoding="utf-8").splitlines()
    if f"usemtl {PAINT}" in lines:
        return
    bridge = K.Model()
    low.footbridge(bridge)
    steel = bridge.polygons[PAINT]
    vertices = [tuple(map(float, line.split()[1:])) for line in lines if line.startswith("v ")]
    vertex_count, uv_count = len(vertices), sum(line.startswith("vt ") for line in lines)
    normal_count = sum(line.startswith("vn ") for line in lines)
    material, targets = "", []
    for index, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        if material != "lt_steel" or not line.startswith("f "):
            continue
        points = [vertices[int(token.split("/")[0]) - 1] for token in line.split()[1:]]
        if all(abs(p[0]) <= low.FLEET + 2 and -18.01 <= p[1] <= 43.01
               and low.FOOTBRIDGE[0] - .51 <= p[2] <= low.FOOTBRIDGE[1] + .51 for p in points):
            targets.append(index)
    if len(targets) != len(steel) * 2:
        raise ValueError(f"Bridge geometry changed: expected {len(steel) * 2} draw triangles, found {len(targets)}")
    if targets != list(range(targets[0], targets[-1] + 1)):
        raise ValueError("The bridge steel faces must be a contiguous block")
    vmdl = path.with_suffix(".vmdl")
    text = vmdl.read_text(encoding="utf-8")
    pattern = r'(?m)^([ \t]*)\{ from = "lt_steel\.vmat" to = "materials/lowtide/lt_steel\.vmat" \},?$'
    match = re.search(pattern, text)
    if not match:
        raise ValueError("Missing original steel remap in the Fleet model")
    additions, new_faces = [], [f"usemtl {PAINT}"]
    for index, (points, normal) in enumerate(steel):
        normal_count += 1
        additions.append(f"vn {K.obj_vector(K.to_world(normal))}")
        tokens = []
        for point, (u, v) in zip(points, bridge.polygon_uvs[(PAINT, index)]):
            vertex_count += 1
            uv_count += 1
            additions.extend((f"v {K.obj_vector(K.to_world(point))}", f"vt {u:.5f} {v:.5f}"))
            tokens.append(f"{vertex_count}/{uv_count}/{normal_count}")
        new_faces.extend((f"f {tokens[0]} {tokens[1]} {tokens[2]}", f"f {tokens[0]} {tokens[2]} {tokens[3]}"))
    new_faces.append("usemtl lt_steel")
    split = next(i for i, line in enumerate(lines) if line.startswith("usemtl "))
    updated = lines[:split] + additions + lines[split:targets[0]] + new_faces + lines[targets[-1] + 1:]
    K.write_text(path, "\n".join(updated) + "\n")
    mtl = path.with_suffix(".mtl")
    K.write_text(mtl, mtl.read_text() + f"newmtl {PAINT}\nKd 1 1 1\nd 1\n")
    remap = f'\n{match.group(1)}{{ from = "{PAINT}.vmat" to = "{RESOURCE}.vmat" }},'
    K.write_text(vmdl, text[:match.end()] + remap + text[match.end():])
    print(f"Updated only the bridge's steel: {len(steel)} faces with normalized edge-wear UVs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.source and args.source.resolve() != SOURCE.resolve():
        shutil.copy2(args.source, SOURCE)
    bake_surface_maps()
    write_materials()
    patch_existing_bridge()
    print(f"Source preserved: {hashlib.sha256(SOURCE.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
