"""Generated oak bench material and grain-aware, softly bevelled timber boards.

rtk proxy python Tools/gunsmith_range_bench.py
Uses the saved ImageGen albedos; normal/roughness maps are approximate technical
derivatives, with restrained relief suitable for sanded, lightly oiled timber.
"""
import io
import itertools
import json
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import map_kit as K

SOURCE = K.ROOT / "Sources/GunsmithRange/bench"
MATERIALS = K.ASSETS / "materials/gunsmith_range"
PAINTS = ("bench_oak", "bench_oak_endgrain")


def metadata(path):
    sidecar = path.with_name(path.name + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL,
            "hc1/gunsmith_range/" + path.relative_to(K.ASSETS).as_posix()))}, indent=2) + "\n")


def save_image(path, data):
    stream = io.BytesIO()
    Image.fromarray(data).save(stream, format="PNG")
    payload = stream.getvalue()
    if path.exists() and path.read_bytes() == payload:
        return
    temp = path.with_name(path.name + ".writing")
    temp.write_bytes(payload)
    temp.replace(path)
    metadata(path)


def materials():
    MATERIALS.mkdir(parents=True, exist_ok=True)
    for paint, source, base_rough in ((PAINTS[0], "oak_longgrain_source.png", .55),
                                     (PAINTS[1], "oak_endgrain_source.png", .63)):
        rgb = np.asarray(Image.open(SOURCE / source).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS))
        value = rgb.astype(np.float32) / 255
        lum = value @ np.array((.2126, .7152, .0722), np.float32)
        # Fine pores affect relief; the broad colour of a growth ring does not.
        relief = gaussian_filter(lum, .7, mode="wrap") - gaussian_filter(lum, 7, mode="wrap")
        dx = (np.roll(relief, -1, axis=1) - np.roll(relief, 1, axis=1)) * 4
        dy = (np.roll(relief, -1, axis=0) - np.roll(relief, 1, axis=0)) * 4
        normal = np.stack((-dx, dy, np.ones_like(lum)), axis=-1)
        normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
        rough = np.clip(base_rough - relief * .8, .43, .76)
        for suffix, pixels in (("color", rgb),
                               ("normal", np.rint((normal + 1) * 127.5).clip(0, 255).astype(np.uint8)),
                               ("roughness", np.rint(rough * 255).astype(np.uint8))):
            save_image(MATERIALS / f"{paint}_{suffix}.png", pixels)
        path = MATERIALS / f"{paint}.vmat"
        resource = f"materials/gunsmith_range/{paint}"
        K.write_text(path, f'''// Generated oak albedo; Tools/gunsmith_range_bench.py bakes the restrained PBR derivatives.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "0"
    g_flRoughnessScaleFactor "1"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
    TextureColor "{resource}_color.png"
    TextureNormal "{resource}_normal.png"
    TextureRoughness "{resource}_roughness.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
''')
        metadata(path)


def plan(world):
    x, y, z = world
    return np.array((-y, x, z), float)


def bevelled_board(model, lo, hi, bench, board):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    centre, half = (lo + hi) / 2, (hi - lo) / 2
    bevel = .14  # 3.6 mm eased edges, retaining the original bench bounds.
    vertices = []
    for signs in itertools.product((-1, 1), repeat=3):
        for axis in range(3):
            corner = half - bevel
            corner[axis] += bevel
            vertices.append(corner * signs)
    vertices = np.array(vertices)
    for vector in itertools.product((-1, 0, 1), repeat=3):
        if not any(vector):
            continue
        normal = K.normalise(vector)
        distances = vertices @ normal
        points = vertices[np.isclose(distances, distances.max(), atol=1e-7)]
        if len(points) < 3:
            continue
        origin = points.mean(axis=0)
        across = K.normalise(points[0] - origin)
        up = np.cross(normal, across)
        points = points[np.argsort(np.arctan2((points - origin) @ up, (points - origin) @ across))] + centre
        end = abs(normal[1]) >= max(abs(normal[0]), abs(normal[2]))
        if end:
            paint = PAINTS[1]
            # Every cut end gets its own understated growth-ring patch, not lengthwise fibers.
            uv = [(.05 + (q[0] - lo[0]) / (hi[0] - lo[0]) * .83,
                   .07 + (q[2] - lo[2]) / (hi[2] - lo[2]) * .78) for q in points]
            if (bench + board) % 2:
                uv = [(1 - u, v) for u, v in uv]
        else:
            paint = PAINTS[0]
            uv = []
            for q in points:
                cross = ((q[0] - lo[0]) / (hi[0] - lo[0]) if abs(normal[2]) >= abs(normal[0])
                         else (q[2] - lo[2]) / (hi[2] - lo[2]))
                u = .04 + board * .23 + cross * .22
                v = .06 + (q[1] - lo[1]) / (hi[1] - lo[1]) * .88
                if (bench + board) % 2:
                    v = 1 - v
                uv.append((u, v))
        model.polygon(paint, [plan(q) for q in points], normal=plan(normal), uv=uv)


def tabletop(model, y, bench):
    # Four actual long timbers instead of fake, oversized transverse plank seams.
    gap = .065
    width = (30 - 3 * gap) / 4
    for board in range(4):
        x = -34 + board * (width + gap)
        bevelled_board(model, (x, y - 85, 30), (x + width, y + 85, 34), bench, board)
    # Retain the original wood collider and dimensions, without tiny gaps that snag players.
    model.box((-y - 85, -34, 30), (-y + 85, -4, 34), None, "wood")


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint] = f"materials/gunsmith_range/{paint}.vmat"


def main():
    import gunsmith_range as G
    materials()
    model = G.level()
    count = K.write_model(G.OUT, G.RESOURCE, "gunsmith_range", model)
    print(f"Bench replacement: {count} triangles, {len(model.boxes)} unchanged collision boxes")


if __name__ == "__main__":
    main()
