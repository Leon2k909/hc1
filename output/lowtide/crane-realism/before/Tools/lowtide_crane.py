"""Lowtide's generated oxide-red painted crane steel.

    rtk proxy python Tools/lowtide_crane.py

Preserve both generated albedos byte-for-byte. Bake thin paint relief, varying
roughness and exposed-steel metalness. Beams keep their 64-inch UVs; the large
machinery-house faces use 128-inch bolted-panel tiles without changing geometry.
"""
import hashlib
import io
import json
import re
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K
import terrain_textures as T

PAINT = "lt_crane_red"
PANELS = "lt_crane_red_panels"
TILE_UNITS = 64.0
PANEL_TILE = 128.0
DIRECTORY = K.ASSETS / "materials/lowtide"
RESOURCE = "materials/lowtide/lt_crane_red"
SOURCE = K.ROOT / "Tools/lowtide_crane_source.png"
PANEL_SOURCE = K.ROOT / "Tools/lowtide_crane_panels_source.png"
REPORT = K.ROOT / "output/lowtide/crane-pass"


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        temporary = path.with_name(path.name + ".writing")
        temporary.write_bytes(data)
        temporary.replace(path)


def metadata(path):
    sidecar = path.with_name(path.name + ".meta")
    if not sidecar.exists():
        key = "hc1/lowtide/crane/" + path.relative_to(K.ASSETS).as_posix()
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, key))}, indent=2) + "\n")


def bake(paint, source, tile, panels=False):
    with Image.open(source) as image:
        if image.width != image.height or image.width < 1024:
            raise ValueError("Expected a square generated steel texture of at least 1024 pixels")
        dimensions = image.size
        # Only the numerical bake input is resampled: Source 2's combined
        # normal/roughness mip filter requires a power-of-two surface grid.
        sample = image.convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS)
    rgb = np.asarray(sample, dtype=np.float32) / 255.0
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    red = (rgb[..., 0] - rgb[..., 1]) / np.maximum(rgb[..., 0], 0.05)
    exposed = 1.0 - T.smoothstep(0.25, 0.50, red)
    warm = (rgb[..., 0] - rgb[..., 2]) / np.maximum(rgb[..., 0], 0.05)
    rust = exposed * T.smoothstep(0.15, 0.40, warm)
    steel = exposed - rust
    fine = gaussian_filter(luminance, 0.65, mode="wrap") - gaussian_filter(luminance, 4.0, mode="wrap")
    # Relief is a thin paint film, in inches, rather than a rocky heightfield
    # made from the red paint's larger colour and lighting variations.
    height = fine * 0.006 - gaussian_filter(exposed, 0.8, mode="wrap") * 0.006
    if panels:
        # Give the generated panel joints a real recess and the small fastener
        # rims shallow relief. Keep the broad colour variation out of height.
        profile_x = gaussian_filter(luminance.mean(axis=0), 1.0)
        profile_y = gaussian_filter(luminance.mean(axis=1), 1.0)
        middle = sample.width // 2
        radius = sample.width // 32
        sx = int(np.argmin(profile_x[middle - radius:middle + radius])) + middle - radius
        sy = int(np.argmin(profile_y[middle - radius:middle + radius])) + middle - radius
        x = np.arange(sample.width, dtype=np.float32)
        width = sample.width / 650.0
        gx = np.maximum.reduce([np.exp(-0.5 * ((x - centre) / width) ** 2)
                                for centre in (0, sx, sample.width - 1)])
        gy = np.exp(-0.5 * ((x - sy) / width) ** 2)
        groove = np.maximum(gx[None, :], gy[:, None])
        near = np.maximum(gaussian_filter(groove, sample.width / 70.0), 0)
        near = np.clip(near * 12.0, 0, 1)
        rim = gaussian_filter(luminance, 1.0) - gaussian_filter(luminance, 12.0)
        height += rim * near * 0.40 - groove * 0.06
    pixels_per_inch = sample.width / tile
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * pixels_per_inch
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * pixels_per_inch
    normal = np.stack((-dx, dy, np.ones_like(luminance)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    roughness = np.clip(0.67 - steel * 0.12 + rust * 0.24 + fine * 0.22, 0.50, 0.94)
    metalness = steel * 0.85
    maps = {
        "normal": np.rint((normal + 1.0) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255.0).astype(np.uint8),
        "metal": np.rint(metalness * 255.0).astype(np.uint8),
    }
    for suffix, array in maps.items():
        path = DIRECTORY / f"{paint}_{suffix}.png"
        buffer = io.BytesIO()
        Image.fromarray(array).save(buffer, format="PNG", optimize=True)
        write_bytes(path, buffer.getvalue())
        metadata(path)
    colour = DIRECTORY / f"{paint}_color.png"
    write_bytes(colour, source.read_bytes())
    metadata(colour)
    if colour.read_bytes() != source.read_bytes():
        raise ValueError("Generated crane albedo was changed")
    REPORT.mkdir(parents=True, exist_ok=True)
    K.write_text(REPORT / f"{paint}-surface.json", json.dumps({
        "material": f"materials/lowtide/{paint}.vmat",
        "albedo_dimensions": dimensions,
        "surface_map_dimensions": sample.size,
        "albedo_sha256": hashlib.sha256(colour.read_bytes()).hexdigest(),
        "generated_albedo_preserved": True,
        "normal_convention": "OpenGL, thin paint/chip relief",
        "tile_inches": tile,
        "roughness_range": [float(roughness.min()), float(roughness.max())],
        "metalness_range": [float(metalness.min()), float(metalness.max())],
        "geometry_and_collisions_changed": False,
    }, indent=2) + "\n")


def write_materials():
    for paint in (PAINT, PANELS):
        write_material(paint)


def write_material(paint):
    for suffix in ("color", "normal", "rough", "metal"):
        if not (DIRECTORY / f"{paint}_{suffix}.png").exists():
            raise FileNotFoundError("Bake the generated Lowtide crane textures first")
    path = DIRECTORY / f"{paint}.vmat"
    resource = f"materials/lowtide/{paint}"
    K.write_text(path, f'''// Tools/lowtide_crane.py: generated weathered oxide-red paint with exposed steel.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "{resource}_color.png"
    TextureNormal "{resource}_normal.png"
    TextureRoughness "{resource}_rough.png"
    TextureMetalness "{resource}_metal.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}}
''')
    metadata(path)


def configure(model):
    for paint, tile in ((PAINT, TILE_UNITS), (PANELS, PANEL_TILE)):
        if paint in model.polygons:
            model.material_overrides[paint] = f"materials/lowtide/{paint}.vmat"
            model.tile_overrides[paint] = tile


def patch_models():
    reports = []
    for name in ("lowtide_dress_east", "lowtide_dress_west"):
        path = K.ASSETS / "models/maps/lowtide" / f"{name}.obj"
        original = path.read_bytes()
        newline = "\r\n" if b"\r\n" in original else "\n"
        lines = original.decode("utf-8").splitlines(keepends=True)
        if f"usemtl {PANELS}" in original.decode("utf-8"):
            print(f"{name}: machinery-house panels already applied")
            continue
        vertices = np.array([list(map(float, line.split()[1:4])) for line in lines if line.startswith("v ")])
        uv_lines = [index for index, line in enumerate(lines) if line.startswith("vt ")]
        selected, selected_uvs, other_uvs = set(), set(), set()
        paint = None
        for index, line in enumerate(lines):
            if line.startswith("usemtl "):
                paint = line.split()[1]
            if not line.startswith("f "):
                continue
            refs = [tuple(map(int, item.split("/"))) for item in line.split()[1:]]
            points = vertices[[item[0] - 1 for item in refs]]
            extents = np.sort(np.ptp(points, axis=0))
            # OBJ axes are (-e, z, n). Only the five large red machinery-house
            # faces meet these dimensions and height bounds; the beams do not.
            panel = (paint == PAINT and extents[1] >= 99.9 and extents[2] >= 119.9
                     and points[:, 1].min() >= 239.9 and points[:, 1].max() <= 340.1
                     and points[:, 2].min() >= -1555.1 and points[:, 2].max() <= -1394.9)
            used = {item[1] for item in refs}
            if panel:
                selected.add(index)
                selected_uvs.update(used)
            else:
                other_uvs.update(used)
        if len(selected) != 20 or selected_uvs & other_uvs:
            raise ValueError(f"{name}: expected 20 independent machinery-house triangles, found {len(selected)}")
        offset = K.uv_offset(name)
        for uv in selected_uvs:
            index = uv_lines[uv - 1]
            u, v = map(float, lines[index].split()[1:3])
            u = offset[0] + (u - offset[0]) * TILE_UNITS / PANEL_TILE
            v = offset[1] + (v - offset[1]) * TILE_UNITS / PANEL_TILE
            lines[index] = f"vt {u:.5f} {v:.5f}" + newline
        output, paint, emitted = [], None, None
        for index, line in enumerate(lines):
            if line.startswith("usemtl "):
                paint = emitted = line.split()[1]
            if line.startswith("f "):
                target = PANELS if index in selected else paint
                if target != emitted:
                    output.append(f"usemtl {target}" + newline)
                    emitted = target
            output.append(line)
        updated = "".join(output).encode("utf-8")
        # Geometry, normals, triangle indices and every collider stay intact.
        for prefix in (b"v ", b"vn ", b"f "):
            assert [line for line in original.splitlines() if line.startswith(prefix)] == \
                   [line for line in updated.splitlines() if line.startswith(prefix)]
        mtl = path.with_suffix(".mtl")
        mtl_data = mtl.read_bytes()
        if f"newmtl {PANELS}".encode() not in mtl_data:
            mtl_data += f"newmtl {PANELS}{newline}Kd 1 1 1{newline}d 1{newline}".encode()
        vmdl = path.with_suffix(".vmdl")
        model_data = vmdl.read_bytes()
        remap = f'\t\t\t\t\t\t\t{{ from = "{PANELS}.vmat" to = "materials/lowtide/{PANELS}.vmat" }},{newline}'.encode()
        marker = re.search(rb'[^\r\n]*\{ from = "lt_crane_red\.vmat"[^\r\n]*\r?\n', model_data)
        if not marker:
            raise ValueError(f"{name}: crane material remap is missing")
        patched_model = model_data[:marker.end()] + remap + model_data[marker.end():]
        assert patched_model.replace(remap, b"", 1) == model_data
        write_bytes(path, updated)
        write_bytes(mtl, mtl_data)
        write_bytes(vmdl, patched_model)
        reports.append({"model": name, "machinery_house_triangles": len(selected), "uv_vertices": len(selected_uvs),
                        "mesh_vertices_normals_triangles_and_collisions_preserved": True})
        print(f"{name}: remapped {len(selected)} machinery-house triangles to bolted panels; geometry/collision unchanged")
    if reports:
        K.write_text(REPORT / "model-remap.json", json.dumps(reports, indent=2) + "\n")


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    bake(PAINT, SOURCE, TILE_UNITS)
    bake(PANELS, PANEL_SOURCE, PANEL_TILE, panels=True)
    write_materials()
    patch_models()
    print("Lowtide cranes: generated oxide-red beam paint and bolted machinery panels, matching relief, "
          "roughness and exposed-metal masks; existing geometry and collision retained.")


if __name__ == "__main__":
    main()
