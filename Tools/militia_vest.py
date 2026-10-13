"""Makes the Militia Fighter's vest: s&box's tactical vest with its POLICE back patch left blank.

The Militia Fighter (`MilitaryUniformStyle.Militia`) wears s&box's citizen tactical vest, whose back patch reads
POLICE. A militia's vest shouldn't, so `MilitaryUniform` gives that style's vest `materials/operators/militia_vest.vmat`,
this script's copy of the vest's material with the lettering taken out of the colour and roughness maps. The normal map
has no lettering (the patch is flat), and the AO map is copied as it is.

s&box ships the vest's normal, roughness and AO maps as PNGs in its citizen addon, but its colour map only compiled.
Read the compiled one out from the editor first (an execute_csharp snippet):

    var m = Material.Load( "models/citizen_clothes/vest/tactical_vest/textures/tactical_vest.vmat" );
    var t = m.GetTexture( "g_tColor" ); t.MarkUsed( 4096 );
    // Run it again once the full mip has streamed in (the first read gives 256 x 256).
    System.IO.File.WriteAllBytes( "<dir>/g_tColor.png", t.GetBitmap( 0 ).ToPng() );

Then: python Tools/militia_vest.py <dir>/g_tColor.png [--preview <png>]

The lettering is on the patch's dark field, x 380-655, y 295-340 of the 1024 maps. Each letter's pixels (bright in the
colour or the roughness map, grown 2 px) are filled from the field round them: a smooth fill solved from the edges
(Laplace), with grain copied from the field's own unlettered pixels so the blank doesn't read as a flat smear.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Assets", "materials", "operators")
SBOX_TEXTURES = ("D:/SteamLibrary/steamapps/common/sbox/addons/citizen/Assets/models/citizen_clothes/vest/"
                 "tactical_vest/Textures/")

# The patch's dark field, and where the letters are on it.
FIELD = (slice(291, 349), slice(349, 680))
# Where the grain is copied from: the field's rows beside the letters, clear of its stitched border.
GRAIN = (slice(295, 341), slice(352, 677))
LETTERS = (slice(295, 341), slice(380, 656))
COLOUR_LETTER = 45  # the field's luminance is 21-25
ROUGH_LETTER = 105  # the field's roughness is 70-76

VMAT = """// Tools/militia_vest.py: s&box's tactical vest (models/citizen_clothes/vest/tactical_vest) with a blank back patch.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0.00"
    TextureColor "materials/operators/militia_vest_color.png"
    TextureNormal "materials/operators/militia_vest_normal.png"
    TextureRoughness "materials/operators/militia_vest_rough.png"
    TextureAmbientOcclusion "materials/operators/militia_vest_ao.png"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}
"""


def grow(mask, px):
    out = mask.copy()
    for _ in range(px):
        g = out.copy()
        g[1:, :] |= out[:-1, :]
        g[:-1, :] |= out[1:, :]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        out = g
    return out


def box_blur(a, r):
    pad = np.pad(a, r, mode="edge")
    c = pad.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    n = 2 * r + 1
    return (c[n:, n:] - c[:-n, n:] - c[n:, :-n] + c[:-n, :-n]) / (n * n)


def fill(channel, hole, field, grain, rng):
    """Fills `hole` (inside `field`) in a 2D float channel."""
    out = channel.copy()
    win = (slice(FIELD[0].start - 8, FIELD[0].stop + 8), slice(FIELD[1].start - 8, FIELD[1].stop + 8))
    out[win] = fill_window(channel[win], hole[win], field[win], grain[win], rng)
    return out


def fill_window(channel, hole, field, grain, rng):
    out = channel.copy()
    known = field & ~hole
    # The smooth fill: start at the field's median and relax to the Laplace solution.
    out[hole] = np.median(channel[known])
    for _ in range(1500):
        avg = (np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 4
        out[hole] = avg[hole]
    # The grain: each filled pixel takes the detail (value less its 5 x 5 mean) of a random unlettered field pixel,
    # kept to the middle 80% so a scratch's or a stain's edge doesn't come out as a speck.
    detail = channel - box_blur(channel, 2)
    ys, xs = np.nonzero(grain & ~grow(hole, 3))
    sample = detail[ys, xs]
    lo, hi = np.percentile(sample, [10, 90])
    out[hole] += np.clip(sample[rng.integers(0, len(sample), hole.sum())], lo, hi)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("colour", help="the vest's compiled colour map, read out from the editor")
    ap.add_argument("--preview", help="write a before/after picture of the patch here")
    args = ap.parse_args()

    colour = np.asarray(Image.open(args.colour).convert("RGB")).astype(np.float64)
    rough = np.asarray(Image.open(SBOX_TEXTURES + "Tactical_vest_Roughness.png").convert("L")).astype(np.float64)
    normal = Image.open(SBOX_TEXTURES + "Tactical_vest_Normal.png").convert("RGB")
    ao = Image.open(SBOX_TEXTURES + "Tactical_vest_Ao.png").convert("L")
    if colour.shape[:2] != rough.shape:
        sys.exit(f"the colour map is {colour.shape[1]} x {colour.shape[0]}: read it again once the full mip has loaded")

    field = np.zeros(rough.shape, bool)
    field[FIELD] = True
    letters = np.zeros(rough.shape, bool)
    letters[LETTERS] = (colour[LETTERS].mean(2) > COLOUR_LETTER) | (rough[LETTERS] > ROUGH_LETTER)
    hole = grow(letters, 2) & field
    grain = np.zeros(rough.shape, bool)
    grain[GRAIN] = True

    rng = np.random.default_rng(7)
    clean = np.stack([fill(colour[..., i], hole, field, grain, rng) for i in range(3)], 2)
    rough_clean = fill(rough, hole, field, grain, rng)

    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(np.clip(clean + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "militia_vest_color.png"))
    Image.fromarray(np.clip(rough_clean + 0.5, 0, 255).astype(np.uint8)).save(os.path.join(OUT, "militia_vest_rough.png"))
    normal.save(os.path.join(OUT, "militia_vest_normal.png"))
    ao.save(os.path.join(OUT, "militia_vest_ao.png"))
    vmat = os.path.join(OUT, "militia_vest.vmat")
    with open(vmat, "w", newline="\n") as f:
        f.write(VMAT)
    print(f"{hole.sum()} px refilled; wrote {OUT}")

    if args.preview:
        box = (330, 270, 700, 370)
        rows = [Image.fromarray(colour.astype(np.uint8)), Image.fromarray(np.clip(clean, 0, 255).astype(np.uint8)),
                Image.fromarray(rough.astype(np.uint8)).convert("RGB"),
                Image.fromarray(np.clip(rough_clean, 0, 255).astype(np.uint8)).convert("RGB")]
        w, h = box[2] - box[0], box[3] - box[1]
        sheet = Image.new("RGB", (w * 2, h * 4 * 2))
        for i, im in enumerate(rows):
            crop = im.crop(box)
            if i < 2:  # the colour map is dark: brighten it to see the patch
                crop = Image.fromarray(np.clip(np.asarray(crop).astype(float) * 4, 0, 255).astype(np.uint8))
            sheet.paste(crop.resize((w * 2, h * 2), Image.NEAREST), (0, i * h * 2))
        sheet.save(args.preview)


if __name__ == "__main__":
    main()
