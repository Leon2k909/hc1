"""Bake Lowtide's generated painted loading-door materials.

Both generated albedos are preserved at their original resolution inside a
power-of-two atlas. Four complete boards repeat between interior groove centres,
at an 11-inch board width and a 160-inch vertical repeat. The existing meshes,
strap hinges, UVs and collision remain usable without a model rebuild.

    rtk proxy python Tools/lowtide_doors.py
"""
import hashlib
import json
import uuid

import numpy as np
from PIL import Image
from scipy import ndimage, signal

import building_textures as BT
import map_kit as K
import terrain_textures as T

DIRECTORY = K.ASSETS / "materials/lowtide"
RESOURCE = "materials/lowtide/lt_door"
VARIANTS = ("lt_door_green", "lt_door_red")
TILE_UNITS = 96.0  # The loading doors' existing world-space mesh UVs.
BOARD_WIDTH = 11.0
VERTICAL_REPEAT = 160.0


def metadata(path):
    sidecar = path.with_name(path.name + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid4())}, indent=2) + "\n")


def source(name):
    return K.ROOT / "Tools" / f"lowtide_door_{name}_source.png"


def surface():
    with Image.open(source("green")) as image:
        if image.width != image.height or image.width < 1024:
            raise ValueError("Expected a square generated door texture of at least 1024 pixels")
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    luminance = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    profile = ndimage.gaussian_filter1d(luminance.mean(axis=0), 1.2)
    joints, _ = signal.find_peaks(-profile, distance=rgb.shape[1] / 10, prominence=0.04)
    if len(joints) < 4:
        raise ValueError("Could not identify the generated texture's vertical board grooves")
    left, right = int(joints[0]), int(joints[-1])
    atlas = 1 << int(np.ceil(np.log2(rgb.shape[0])))
    region = ((left + 0.5) / atlas, 0.5 / atlas,
              (right - left) / atlas, (rgb.shape[0] - 1) / atlas)
    scale = (TILE_UNITS / (BOARD_WIDTH * (len(joints) - 1)), TILE_UNITS / VERTICAL_REPEAT)
    return rgb, luminance, joints, atlas, region, scale


def pack(array, atlas, path):
    repetitions = (int(np.ceil(atlas / array.shape[0])), int(np.ceil(atlas / array.shape[1])))
    if array.ndim == 3:
        repetitions += (1,)
    packed = np.tile(array, repetitions)[:atlas, :atlas]
    Image.fromarray(packed).save(path, optimize=True)
    metadata(path)


def bake():
    rgb, luminance, joints, atlas, _, _ = surface()
    size = rgb.shape[0]
    x = np.arange(size, dtype=np.float32)
    groove = np.max(np.exp(-0.5 * ((x[None, :] - joints[:, None]) / (size / 420.0)) ** 2), axis=0)
    groove = np.broadcast_to(groove, luminance.shape)
    # Paint/wood colour is not itself a height field: only the grooves, tiny
    # paint flakes and fine grain get relief. This avoids inflated knots.
    green = (rgb[..., 1] - rgb[..., 0]) / np.maximum(rgb[..., 1], 0.05)
    bare = 1.0 - T.smoothstep(0.02, 0.13, green)
    detail = luminance - ndimage.gaussian_filter(luminance, 1.5, mode="wrap")
    height = 0.65 - groove * 0.30 - bare * 0.02 + detail * 0.18
    normal = BT.gl_normals(height, 4.0 * size / 1024.0)
    roughness = np.clip(0.78 + bare * 0.14 + groove * 0.08 + np.abs(detail) * 0.25, 0.76, 0.96)
    ao = 1.0 - groove * 0.14
    maps = {
        "normal": np.rint((normal + 1.0) * 127.5).clip(0, 255).astype(np.uint8),
        "rough": np.rint(roughness * 255.0).astype(np.uint8),
        "ao": np.rint(ao * 255.0).astype(np.uint8),
    }
    for suffix, array in maps.items():
        pack(array, atlas, DIRECTORY / f"lt_door_{suffix}.png")
    for name in ("green", "red"):
        with Image.open(source(name)) as image:
            if image.size != (size, size):
                raise ValueError(f"The {name} door texture must match the green source dimensions")
            colour = np.asarray(image.convert("RGB"))
        path = DIRECTORY / f"lt_door_{name}_color.png"
        pack(colour, atlas, path)
        with Image.open(path) as packed:
            if not np.array_equal(np.asarray(packed)[:size, :size], colour):
                raise ValueError(f"Packing changed the generated {name} albedo")


def material_text(name, region, scale):
    return f'''// Tools/lowtide_doors.py: generated painted vertical timber, matching grain and groove relief.
"Layer0"
{{
    shader "shaders/hc1_lowtide_door.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "{RESOURCE}_{name}_color.png"
    TextureNormal "{RESOURCE}_normal.png"
    TextureRoughness "{RESOURCE}_rough.png"
    TextureAmbientOcclusion "{RESOURCE}_ao.png"
    g_vDoorRegion "[{region[0]:.8f} {region[1]:.8f} {region[2]:.8f} {region[3]:.8f}]"
    g_vDoorScale "[{scale[0]:.8f} {scale[1]:.8f}]"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}}
'''


def write_materials():
    _, _, _, _, region, scale = surface()
    for name in ("green", "red"):
        if not (DIRECTORY / f"lt_door_{name}_color.png").exists():
            raise FileNotFoundError("Bake the generated Lowtide door textures first")
        path = DIRECTORY / f"lt_door_{name}.vmat"
        K.write_text(path, material_text(name, region, scale))
        metadata(path)


def main():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    bake()
    write_materials()
    _, _, joints, atlas, region, scale = surface()
    metadata(K.ASSETS / "shaders/hc1_lowtide_door.shader")
    report = {
        "atlas_size": atlas,
        "board_joint_pixels": joints.tolist(),
        "sample_region": region,
        "uv_scale": scale,
        "board_width_inches": BOARD_WIDTH,
        "vertical_repeat_inches": VERTICAL_REPEAT,
        "generated_albedos_preserved": True,
        "source_sha256": {name: hashlib.sha256(source(name).read_bytes()).hexdigest() for name in ("green", "red")},
        "geometry_and_collisions_changed": False,
    }
    output = K.ROOT / "output/lowtide/doors-pass"
    output.mkdir(parents=True, exist_ok=True)
    K.write_text(output / "materials.json", json.dumps(report, indent=2) + "\n")
    print(f"Baked green/red Lowtide doors: {atlas}px atlases, {len(joints) - 1} boards per tile, "
          f"UV scale {scale[0]:.6f}, {scale[1]:.6f}; generated albedos unchanged.")


if __name__ == "__main__":
    main()
