"""Boxyard perimeter wall v1: the weathered base-zone textures and the two materials (boxyard-model session, 2026-11-06).

Nothing here is painted from nothing: the base zone (the plinth and the first 16 in course, z 0..24) is cut from the SAME
real concrete scan the field uses (Spillway's Poly Haven `concrete_wall_009`, CC0), at the same true scale (48 in = 2048 px,
42.7 px/in), made seamless along its length, then weathered the way the old wall was (a dirty, mossy foot) by multiplying
rain-splash dirt and algae/moss tints onto the scan, so the pores, tie holes and streaks of the real surface still show
through. The field, coping and piers use the scan files as they are (no copies but the OpenGL normal map, a byte-identical
copy of the Collider finish's conversion so this model cannot dangle if that trial is reverted).

    python pw_tex.py            writes Assets/materials/boxyard/perimeter_wall_v1/*
"""
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "Assets/materials/boxyard/perimeter_wall_v1"
SCAN = ROOT / "Assets/materials/spillway/scans"
DIFF = SCAN / "concrete_wall_009_diff_2k.jpg"
ROUGH = SCAN / "concrete_wall_009_rough_2k.jpg"
NORMAL_GL = ROOT / "Assets/materials/collider/finish-v1/concrete_wall_009_nor_gl_2k.jpg"

W, H = 2048, 1024            # 48 in x 24 in at 42.7 px/in
TOP_ROWS, BOT_ROWS = 683, 341        # z 24..8 (a 16 in course) and z 8..0 (the plinth)
B = 70                        # cross-fade width of the seamless joins


def load(path, mode):
    return np.asarray(Image.open(path).convert(mode), np.float32)


def seamless_pair(p1, p2):
    w1, w2 = p1.shape[1], p2.shape[1]
    ramp = np.linspace(0.0, 1.0, B, dtype=np.float32)[None, :, None]
    j1 = p1[:, w1 - B:] * (1 - ramp) + p2[:, :B] * ramp
    j2 = p2[:, w2 - B:] * (1 - ramp) + p1[:, :B] * ramp
    return np.concatenate([j2, p1[:, B:w1 - B], j1, p2[:, B:w2 - B]], axis=1)


def resize_rows(img, rows):
    if img.shape[0] == rows:
        return img
    ch = img.shape[2]
    chans = [np.asarray(Image.fromarray(img[:, :, c]).resize((img.shape[1], rows), Image.BILINEAR)) for c in range(ch)]
    return np.stack(chans, axis=2)


def assemble(img, normal=False):
    """ The 1024 x 2048 base strip from the scan: the top zone from two different board rows, the plinth from two others,
    each made seamless. Rows of the scan between its joint lines (692..1358 and 1372..2040, 10..676) are used. """
    if img.ndim == 2:
        img = img[:, :, None]
    x1, x2 = 60, 60
    top1 = resize_rows(img[692:1359, x1:x1 + 1100], TOP_ROWS)
    top2 = resize_rows(img[1372:2041, x2:x2 + 1088], TOP_ROWS)
    bot1 = img[120:120 + BOT_ROWS, x1:x1 + 1100]
    bot2 = img[1480:1480 + BOT_ROWS, x2:x2 + 1088]
    top = seamless_pair(top1, top2)
    bot = seamless_pair(bot1, bot2)
    out = np.concatenate([top, bot], axis=0)
    if normal:
        v = out / 255.0 * 2 - 1
        v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-6)
        out = (v * 0.5 + 0.5) * 255.0
    return out


def fnoise(h, w, seed, beta, ay=1.0):
    """ Periodic 1/f^beta noise in 0..1 (inherently tileable). ay > 1 stretches its features up and down (rain runs). """
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * ay
    fx = np.fft.fftfreq(w)[None, :]
    r = np.sqrt(fx * fx + fy * fy)
    r[0, 0] = 1.0
    f = f / (r ** (beta / 2.0))
    f[0, 0] = 0
    n = np.real(np.fft.ifft2(f))
    n = (n - n.mean()) / (n.std() + 1e-9)
    return np.clip(n * 0.22 + 0.5, 0.0, 1.0)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def weather():
    """ ( splash dirt mask, moss mask, pit speckle, z in inches per row ): a grimy foot with sparse growth, like the old
    wall's, not a painted band. """
    z = (24.0 * (1.0 - (np.arange(H, dtype=np.float32) + 0.5) / H))[:, None] * np.ones((1, W), np.float32)
    n_run = fnoise(H, W, 11, 2.2, ay=7.0)      # rain runs, long up and down
    n_blot = fnoise(H, W, 12, 2.0)             # blotches of a few inches
    n_grain = fnoise(H, W, 13, 1.1)
    n_moss = fnoise(H, W, 21, 2.0)
    n_moss2 = fnoise(H, W, 22, 1.0)
    dirt_amt = np.clip((13.0 - z) / 13.0, 0.0, 1.0)
    dirt = smoothstep(0.10, 0.95, dirt_amt ** 0.9 + 0.55 * (n_run - 0.5) + 0.35 * (n_blot - 0.5) + 0.12 * (n_grain - 0.5))
    moss_amt = np.clip((11.0 - z) / 11.0, 0.0, 1.0)
    moss = smoothstep(0.66, 0.86, 0.50 * moss_amt + 0.95 * (n_moss - 0.5) + 0.45 * (n_moss2 - 0.5) + 0.27)
    speck = (fnoise(H, W, 33, 0.8) > 0.70).astype(np.float32) * (0.15 + 0.35 * dirt_amt)
    return dirt, moss, speck, z


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    diff = assemble(load(DIFF, "RGB"))
    rough = assemble(load(ROUGH, "L"))[:, :, 0]
    nor = assemble(load(NORMAL_GL, "RGB"), normal=True)
    dirt, moss, speck, z = weather()
    dirt_colour = np.array([0.72, 0.69, 0.64], np.float32)
    moss_colour = np.array([0.60, 0.68, 0.54], np.float32)
    f = 1.0 - dirt[:, :, None] * (1.0 - dirt_colour[None, None, :])
    f = f * (1.0 - moss[:, :, None]) + moss[:, :, None] * moss_colour[None, None, :]    # moss replaces the grime, it doesn't stack on it
    f = f * (1.0 - 0.45 * speck[:, :, None])
    f = f * (1.0 - 0.14 * np.clip((10.0 - z) / 10.0, 0, 1)[:, :, None] ** 2)    # splash-wet foot
    colour = np.clip(diff * f, 0, 255).astype(np.uint8)
    wet = np.clip(0.55 * dirt + 0.75 * moss, 0.0, 1.0)
    r = np.clip(rough + (0.93 * 255.0 - rough) * wet, 0, 255).astype(np.uint8)
    Image.fromarray(colour).save(OUT / "pw_base_color.jpg", quality=94, subsampling=0)
    Image.fromarray(np.clip(nor, 0, 255).astype(np.uint8)).save(OUT / "pw_base_normal.jpg", quality=94, subsampling=0)
    Image.fromarray(r, "L").save(OUT / "pw_base_rough.png", optimize=True)
    shutil.copyfile(NORMAL_GL, OUT / "pw_concrete_normal.jpg")
    return colour


VMAT = """// Sources/Boxyard/perimeter-wall-v1/pw_tex.py ({note})
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "{color}"
    TextureNormal "{normal}"
    TextureRoughness "{rough}"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[{tint}]"
    g_flModelTintAmount "1.0"
}}
"""


def write_vmats():
    (OUT / "pw_concrete.vmat").write_text(VMAT.format(
        note="the field, coping and piers: Spillway's Poly Haven concrete_wall_009 scan, used as it is",
        color="materials/spillway/scans/concrete_wall_009_diff_2k.jpg",
        normal="materials/boxyard/perimeter_wall_v1/pw_concrete_normal.jpg",
        rough="materials/spillway/scans/concrete_wall_009_rough_2k.jpg",
        tint="0.93 0.96 1.0 1.0"), newline="\n")
    (OUT / "pw_base.vmat").write_text(VMAT.format(
        note="the plinth and first course: the same scan, cut for the foot and weathered (dirt and moss)",
        color="materials/boxyard/perimeter_wall_v1/pw_base_color.jpg",
        normal="materials/boxyard/perimeter_wall_v1/pw_base_normal.jpg",
        rough="materials/boxyard/perimeter_wall_v1/pw_base_rough.png",
        tint="0.93 0.96 1.0 1.0"), newline="\n")


if __name__ == "__main__":
    c = build()
    write_vmats()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
    print("base colour mean", c.reshape(-1, 3).mean(0).round(1), "top 100 rows", c[:100].reshape(-1, 3).mean(0).round(1),
          "bottom 100 rows", c[-100:].reshape(-1, 3).mean(0).round(1))
