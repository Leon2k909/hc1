"""Neutral soil, bark fragments and shallow relief inside the existing palm beds."""
import math
from pathlib import Path
import shutil

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import riverdale_parts as P

ROOT = Path(__file__).resolve().parents[1]
PAINT = "vr_palm_mulch"
PREFIX = "materials/veridant/palm-mulch-v1"
TILE = 30.0  # inches covered by the photographed surface
INNER = 30.7


def build_into(model, base, seed=0):
    e, n, z = map(float, base)
    rng = np.random.default_rng(41100 + abs(int(seed)))
    phase = rng.uniform(0, math.tau, 3)
    uv_offset = rng.uniform(0, 1, 2)

    def height(x, y):
        # A little settlement against the edging; the fill stays below its 3" rim.
        edge = np.clip((INNER - max(abs(x), abs(y))) / 4.0, 0, 1)
        waves = (.14 * math.sin(x * .29 + phase[0]) * math.cos(y * .24 + phase[1])
                 + .065 * math.sin(x * .73 + y * .53 + phase[2]))
        root = .26 * math.exp(-(x*x + y*y) / (2 * 14.0**2))
        return z + .28 + edge * (.27 + waves + root)

    def normal(x, y):
        step = .04
        return P.unit((-(height(x + step, y) - height(x - step, y)) / (2 * step),
                       -(height(x, y + step) - height(x, y - step)) / (2 * step), 1))

    def uv(points):
        # UVs are explicit so the world-sized grain is retained in every bed.
        return [((p[0] - e) / TILE + uv_offset[0],
                 (p[1] - n) / TILE + uv_offset[1]) for p in points]

    grid = np.linspace(-INNER, INNER, 21)
    for i in range(20):
        for j in range(20):
            coordinates = [(grid[x], grid[y]) for x, y in
                           ((i, j), (i+1, j), (i+1, j+1), (i, j+1))]
            points = [np.array((e+x, n+y, height(x, y))) for x, y in coordinates]
            P.card(model, PAINT, points, (0, 0, 1), uv=uv(points),
                   normals=[normal(x, y) for x, y in coordinates])

    # The texture supplies fine aggregate; these embedded irregular fragments
    # supply real grazing highlights and small contact shadows at close range.
    count = 0
    while count < 120:
        x, y = rng.uniform(-INNER+1.8, INNER-1.8, 2)
        if x*x+y*y < 13.2**2:
            continue
        yaw = rng.uniform(0, math.tau)
        right = np.array((math.cos(yaw), math.sin(yaw)))
        across = np.array((-right[1], right[0]))
        length = rng.uniform(.70, 2.20)
        width = length*rng.uniform(.26, .48)
        rise = rng.uniform(.11, .32)
        outline = [(-.52, -.18), (-.27, -.48), (.34, -.39),
                   (.53, .08), (.20, .47), (-.39, .40)]
        top, bottom = [], []
        for a, b in outline:
            delta = right*(a*length*rng.uniform(.90, 1.10)) + across*(b*width)
            xx, yy = x+delta[0], y+delta[1]
            floor = height(xx, yy)
            top.append(np.array((e+xx, n+yy, floor+rise*rng.uniform(.35, .80))))
            bottom.append(np.array((e+xx, n+yy, floor-.055)))
        ridge = np.array((e+x, n+y, height(x, y)+rise))
        for k in range(6):
            nxt = (k+1) % 6
            points = (top[k], top[nxt], ridge)
            P.card(model, PAINT, points, (0, 0, 1), uv=uv(points))
            points = (bottom[k], bottom[nxt], top[nxt], top[k])
            towards = (top[k]+top[nxt])/2 - np.array((e+x, n+y, z))
            towards[2] = 0
            tangent = P.unit(top[nxt]-top[k])
            side_uv = [(float(np.dot(p, tangent)/TILE+uv_offset[0]),
                        float(p[2]/TILE+uv_offset[1])) for p in points]
            P.card(model, PAINT, points, towards, uv=side_uv)
        count += 1

    model.material_overrides[PAINT] = "materials/veridant/vr_palm_mulch.vmat"
    model.tile_overrides[PAINT] = TILE
    return {"fragments": count, "surface_triangles": 800, "inner_half_width": INNER}


def write_materials(directory):
    """Keep the generated albedo intact; derive restrained normal/roughness maps."""
    directory = Path(directory)
    folder = directory / "palm-mulch-v1"
    folder.mkdir(parents=True, exist_ok=True)
    source = ROOT / "Sources/Veridant/palm-mulch-v1/soil-bark-albedo-generated.png"
    shutil.copyfile(source, folder / "soil-bark-color.png")
    # The engine's packed normal mip generator requires power-of-two dimensions.
    rgb = np.asarray(Image.open(source).convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS), dtype=float) / 255
    grey = rgb @ np.array((.2126, .7152, .0722))
    # This is a small visual relief estimate, not a measured displacement scan.
    relief = .018*(gaussian_filter(grey, 1.15) - gaussian_filter(grey, 32))
    dx = (np.roll(relief, -1, 1) - np.roll(relief, 1, 1)) / (2*TILE/grey.shape[1])
    dy = (np.roll(relief, -1, 0) - np.roll(relief, 1, 0)) / (2*TILE/grey.shape[0])
    normals = np.stack((-dx, dy, np.ones_like(dx)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1)[..., None]
    Image.fromarray(np.clip((normals*.5+.5)*255, 0, 255).astype(np.uint8)).save(folder / "soil-bark-normal.png")
    roughness = np.clip(.92 - .09*gaussian_filter(grey, 2), .84, .96)
    Image.fromarray((roughness*255).astype(np.uint8)).save(folder / "soil-bark-rough.png")
    (directory / "vr_palm_mulch.vmat").write_text(
        '// Tools/veridant_palm_mulch.py\n"Layer0"\n{\n'
        '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
        '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n'
        f'    TextureColor "{PREFIX}/soil-bark-color.png"\n'
        f'    TextureNormal "{PREFIX}/soil-bark-normal.png"\n'
        f'    TextureRoughness "{PREFIX}/soil-bark-rough.png"\n'
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
        '    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1.0"\n}\n')
