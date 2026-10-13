"""Generated timber for Lowtide's warehouse stairs, mapped along each step."""
import io
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K

SOURCE = Path(__file__).with_name("lowtide_stairs_source.png")
OUT = K.ASSETS / "materials/lowtide/stairs"
RESOURCE = "materials/lowtide/stairs"
TREAD = "lt_stair_wood"
RISER = "lt_stair_riser"


def write_materials():
    OUT.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as image:
        rgb = np.asarray(image.convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS), np.float32) / 255
    luminance = rgb @ np.array((.2126, .7152, .0722), np.float32)
    grain = ndimage.gaussian_filter(luminance, .7, mode="wrap") - ndimage.gaussian_filter(luminance, 7, mode="wrap")
    pores = np.clip((.29 - luminance) * 2, 0, .5)
    rough = np.clip(.77 + pores * .2 - grain * .15, .65, .92)
    height = grain * .10 - pores * .006
    dy, dx = np.gradient(ndimage.gaussian_filter(height, .7, mode="wrap"))
    normal = np.dstack((-dx * 4, dy * 4, np.ones_like(dx)))
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    for channel, data in (("color", rgb * 255), ("normal", (normal * .5 + .5) * 255), ("rough", rough * 255)):
        stream = io.BytesIO()
        Image.fromarray(np.clip(np.rint(data), 0, 255).astype(np.uint8)).save(stream, format="PNG", optimize=True)
        path, payload = OUT / f"wood_{channel}.png", stream.getvalue()
        if not path.exists() or path.read_bytes() != payload:
            path.write_bytes(payload)
    for paint, tint in ((TREAD, 1), (RISER, .72)):
        text = f'''// Tools/lowtide_stairs.py; generated timber scan
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "0"
    g_flRoughnessScaleFactor "1"
    g_vColorTint "[{tint} {tint} {tint} 1]"
    g_flModelTintAmount "1"
    TextureColor "{RESOURCE}/wood_color.png"
    TextureNormal "{RESOURCE}/wood_normal.png"
    TextureRoughness "{RESOURCE}/wood_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
}}
'''
        K.write_text(OUT / f"{paint}.vmat", text)


def configure(model):
    for paint in (TREAD, RISER):
        if paint in model.polygons:
            model.material_overrides[paint] = f"{RESOURCE}/{paint}.vmat"


def face_uv(paint, points, e0, n0, top, step_z, index):
    """Grain across the full tread; varied crops stay inside the scan without a wrapping seam."""
    points = np.asarray(points, float)
    offset_u = ((index * 0.38196601125) % 1) * .15
    offset_v = ((index * 0.61803398875) % 1) * .60
    # Boards can be laid either way round; alternate crops to break up recurring knots.
    across = points[:, 0].max() - points[:, 0] if index % 2 else points[:, 0] - e0
    u = across / 64 + offset_u
    v = (points[:, 1] - n0) / 32 if paint == TREAD else (points[:, 2] - (top - step_z)) / 32
    return np.column_stack((u, v + offset_v))


def step(model, e0, e1, na, nb, top, base, step_z, index, side):
    starts = {paint: len(model.polygons[paint]) for paint in (TREAD, RISER)}
    model.box((e0, min(na, nb), base), (e1, max(na, nb), top),
              {"+z": TREAD, "default": side, "+n" if nb > na else "-n": RISER,
               "-n" if nb > na else "+n": None, "-z": None})
    for paint, start in starts.items():
        for i in range(start, len(model.polygons[paint])):
            points, _ = model.polygons[paint][i]
            model.polygon_uvs[(paint, i)] = face_uv(paint, points, e0, min(na, nb), top, step_z, index).tolist()


if __name__ == "__main__":
    write_materials()
    print("Lowtide stair timber and surface maps saved")
