"""Write Lowtide's shallow-water material, using continuous, pixel-filtered shader waves."""

from pathlib import Path
import json
import uuid

import numpy as np
from PIL import Image

import map_kit as K
import lowtide_water_filter as W

DIRECTORY = K.ASSETS / "materials/lowtide"
MATERIAL = DIRECTORY / "lt_water.vmat"
SHADER = K.ASSETS / "shaders/hc1_lowtide_water.shader"
NORMALS = DIRECTORY / "sea"


def bake_wave_normals():
    """Deterministic tileable spectral sea normals; cross-swells prevent repeated straight bands.

    Independent wind-angle fields scroll and repeat at different world scales.
    The tile wraps because every frequency is an integer number of cycles.
    """
    NORMALS.mkdir(parents=True, exist_ok=True)
    n = 1024
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.rfftfreq(n)[None, :] * n
    k = np.sqrt(kx * kx + ky * ky)
    for name, seed, angle, cycles, spread, strength in (
        ("lt_ocean_swell_normal.png", 61472, 0.43, 105, .67, .24),
        ("lt_ocean_chop_normal.png", 19283, -0.92, 175, .9, .31),
    ):
        path = NORMALS / name
        if path.exists():
            continue
        rng = np.random.default_rng(seed)
        # A directional but broad ocean wave spectrum: no single straight crest
        # crosses the texture, and near-zero or unresolved frequencies vanish.
        parallel = kx * np.cos(angle) + ky * np.sin(angle)
        cross = -kx * np.sin(angle) + ky * np.cos(angle)
        directional = np.exp(-.5 * (cross / (3.0 + spread * np.abs(parallel))) ** 2)
        spectrum = (1.0 - np.exp(-(k / 5.0) ** 4)) * np.exp(-(k / cycles) ** 4)
        spectrum *= (k + 1.0) ** -.63 * (.16 + .84 * directional)
        phases = rng.standard_normal(k.shape) + 1j * rng.standard_normal(k.shape)
        height = np.fft.irfft2(phases * spectrum, s=(n, n)).astype(np.float32)
        dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * .5
        dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * .5
        gain = strength / max(np.sqrt((dx * dx + dy * dy).mean() * .5), 1e-8)
        dx *= gain
        dy *= gain
        inv_length = 1.0 / np.sqrt(1.0 + dx * dx + dy * dy)
        packed = np.stack((-dx * inv_length, -dy * inv_length, inv_length), -1)
        Image.fromarray(np.rint(np.clip(packed * .5 + .5, 0, 1) * 255).astype(np.uint8), "RGB").save(path)
        metadata(path)


def reflection_component(ids, key):
    return K.component(ids, "Facepunch.LowtideWaterReflections", f"{key}/reflections",
                       WaterHeight=-137, MaximumWidth=960)


def apply_scene(scene, L):
    water = next(o for o in next(o for o in scene["GameObjects"] if o.get("Name") == "Lowtide")["Children"]
                 if o.get("Name") == "Water")
    water["Components"][:] = [c for c in water["Components"] if c["__type"] != "Facepunch.LowtideWaterReflections"]
    water["Components"].append(reflection_component(L.ids, "world/lowtide_water"))


def metadata(path):
    sidecar = Path(str(path) + ".meta")
    if not sidecar.exists():
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid4())}, indent=2) + "\n")


def write_materials():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    bake_wave_normals()
    material = '''// Tools/lowtide_water.py: filtered continuous waves and depth-based absorption.
"Layer0"
{
    shader "shaders/hc1_lowtide_water.shader"
    OceanSwell "materials/lowtide/sea/lt_ocean_swell_normal.png"
    OceanChop "materials/lowtide/sea/lt_ocean_chop_normal.png"
    g_vWaterColor "[0.014 0.022 0.018]"
    g_vWaterFlow "[-2.1 0.65]"
    g_flRippleTile "60"
    g_flRippleStrength "0.52"
    g_flWaterRoughness "0.22"
    g_flAbsorptionDistance "11"
    g_flBankFade "4"
}
'''
    filtered_shader = K.ASSETS / W.SHADER.removeprefix('Assets/')
    K.write_text(filtered_shader, W.shader())
    filtered_meta = Path(str(filtered_shader) + '.meta')
    if not filtered_meta.exists():
        K.write_text(filtered_meta, json.dumps({'guid': str(uuid.uuid5(uuid.NAMESPACE_URL, W.SHADER[7:]))}, indent=2) + '\n')
    K.write_text(MATERIAL, W.material(material))
    metadata(MATERIAL)
    metadata(SHADER)


if __name__ == "__main__":
    write_materials()
    print(f"Wrote {MATERIAL.name}: continuous waves, screen-footprint filtering and transparent shallows")
