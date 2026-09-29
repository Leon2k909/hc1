"""Build the per-perk artwork from the illustrated labels: python Assets/Perks/build_perk_art.py

- <perk>_poster.png: the dispenser's front panel. The label is square but the panel is 29.6 x 42.6,
  so it gets a name plate above and an effect plate below instead of being stretched to fit.
- <perk>_sign.png / <perk>_sign_glow.png: the lit name sign on top of the dispenser (colour + self-illum mask).
- aged_enamel_neutral.png: the cabinet enamel, white-balanced to grey so each perk tints it its own colour.
- ui/zombies/perks/<perk>.png: round HUD badges cut from the label's central medallion.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
FONT = ASSETS / "fonts" / "Dinish-Bold.ttf"
UI = ASSETS / "ui" / "zombies" / "perks"

# name, effect line, sign colour (the label's own ink colour, lifted so it reads as lit glass)
PERKS = {
    "irontonic": ("IRON TONIC", "MORE HEALTH", (255, 72, 58)),
    "boltsoda": ("BOLT SODA", "FASTER RELOADS", (84, 235, 110)),
    "hotshot": ("HOT SHOT", "FIRE RATE & DAMAGE", (255, 190, 70)),
    "secondwind": ("SECOND WIND", "FASTER REVIVES", (96, 170, 255)),
    "fleetfoot": ("FLEET FOOT", "MOVE FASTER", (255, 140, 40)),
}

INK = (39, 38, 35)        # the labels' dark print
CREAM = (228, 211, 176)   # the labels' paper
OLIVE = (88, 94, 62)      # the labels' frame green

POSTER_W, POSTER_H = 1254, 1805          # 29.6 x 42.6, the dispenser's display window
SIGN_W, SIGN_H = 1024, 256               # 34 x 8.6, the top sign's face
rng = np.random.default_rng(7)


def grain(size, strength):
    """Print grain and specks, so flat plates match the aged labels."""
    w, h = size
    noise = rng.normal(0, strength, (h, w, 1))
    specks = (rng.random((h, w, 1)) > 0.9985) * rng.uniform(-60, 40, (h, w, 1))
    return Image.fromarray(np.clip(128 + noise + specks, 0, 255).astype(np.uint8).repeat(3, 2)).filter(ImageFilter.GaussianBlur(0.6))


def apply_grain(image, strength=9):
    g = np.asarray(grain(image.size, strength), float) - 128
    return Image.fromarray(np.clip(np.asarray(image, float) + g, 0, 255).astype(np.uint8))


def fit_font(draw, text, max_width, size, spacing_em=0.08):
    while True:
        font = ImageFont.truetype(str(FONT), size)
        spacing = size * spacing_em
        width = sum(draw.textlength(c, font=font) for c in text) + spacing * (len(text) - 1)
        if width <= max_width or size < 12:
            return font, spacing, width
        size -= 4


def spaced_text(draw, centre, text, font, spacing, width, fill):
    x = centre[0] - width / 2
    for c in text:
        draw.text((x, centre[1]), c, font=font, fill=fill, anchor="lm")
        x += draw.textlength(c, font=font) + spacing


def rivet(label):
    """The brass rivet from the label's top-left corner, with its round alpha."""
    r = 34
    crop = label.crop((68 - r, 60 - r, 68 + r, 60 + r)).convert("RGBA")
    mask = Image.new("L", (r * 8, r * 8), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, r * 8 - 1, r * 8 - 1), fill=255)
    crop.putalpha(mask.resize(crop.size, Image.LANCZOS))
    return crop


def plate(label, size, text, text_height, rule_colour):
    """A dark enamel plate with an olive frame, cream lettering and corner rivets."""
    w, h = size
    img = Image.new("RGB", size, INK)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w - 1, h - 1), outline=OLIVE, width=22)
    d.rectangle((30, 30, w - 31, h - 31), outline=CREAM, width=5)
    font, spacing, width = fit_font(d, text, w - 260, text_height)
    spaced_text(d, (w / 2, h / 2 + 4), text, font, spacing, width, CREAM)
    if rule_colour:
        d.rectangle((w / 2 - width / 2, h / 2 + text_height * 0.46, w / 2 + width / 2, h / 2 + text_height * 0.46 + 8), fill=rule_colour)
    img = apply_grain(img)
    rv = rivet(label)
    for x in (70, w - 70):
        img.paste(rv, (x - rv.width // 2, h // 2 - rv.height // 2), rv)
    return img


def poster(key, label):
    name, effect, colour = PERKS[key]
    header = 330
    footer = POSTER_H - POSTER_W - header
    out = Image.new("RGB", (POSTER_W, POSTER_H), INK)
    out.paste(plate(label, (POSTER_W, header), name, 190, colour), (0, 0))
    out.paste(label, (0, header))
    out.paste(plate(label, (POSTER_W, footer), effect, 92, None), (0, header + POSTER_W))
    return out


def sign(key):
    """Smoked glass with the name in lit glass letters. Returns (colour, self-illum mask)."""
    name, _, colour = PERKS[key]
    w, h = SIGN_W, SIGN_H
    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    font, spacing, width = fit_font(gd, name, w - 150, 150, 0.1)
    spaced_text(gd, (w / 2, h / 2 + 6), name, font, spacing, width, 255)
    gd.rectangle((18, 18, w - 19, h - 19), outline=150, width=6)

    halo = glow.filter(ImageFilter.GaussianBlur(14))
    base = np.asarray(apply_grain(Image.new("RGB", (w, h), (14, 15, 13)), 4), float)
    c = np.array(colour, float)
    lit = np.asarray(glow, float)[..., None] / 255
    haze = np.asarray(halo, float)[..., None] / 255 * 0.45
    core = np.minimum(255, c + (255 - c) * 0.45)       # letters burn a little whiter in the middle
    colour_img = base * (1 - np.maximum(lit, haze)) + c * haze + core * lit
    mask = np.clip(np.asarray(glow, float) + np.asarray(halo, float) * 0.5, 0, 255)
    return Image.fromarray(np.clip(colour_img, 0, 255).astype(np.uint8)), Image.fromarray(mask.astype(np.uint8))


def badge(label, size=128):
    r = 545
    crop = label.crop((627 - r, 627 - r, 627 + r, 627 + r)).resize((size, size), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    crop.putalpha(mask.resize((size, size), Image.LANCZOS))
    return crop


def neutral_enamel():
    """White-balance the seafoam enamel to grey (paint ~0.8) and keep its chips and grime."""
    src = np.asarray(Image.open(HERE / "aged_enamel_seafoam.png").convert("RGB"), float)
    paint = np.median(src.reshape(-1, 3), axis=0)
    out = src / paint * 204
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def vmat(path, lines):
    body = "\n".join(f'\t"{k}" "{v}"' for k, v in lines)
    path.write_text(f'"Layer0"\n{{\n{body}\n}}\n', encoding="utf-8")


def main():
    UI.mkdir(parents=True, exist_ok=True)
    neutral_enamel().save(HERE / "aged_enamel_neutral.png")
    vmat(HERE / "aged_enamel.vmat", [
        ("shader", "shaders/simple.shader"), ("TextureColor", "Perks/aged_enamel_neutral.png"),
        ("g_vColorTint", "[1 1 1 1]"), ("g_flModelTintAmount", "1.000"),
        ("g_flMetalness", "0.250"), ("g_flRoughnessScaleFactor", "0.560"), ("g_bFogEnabled", "1")])
    # Lamps and the switch: lit in the renderer's tint.
    Image.new("RGB", (16, 16), (255, 255, 255)).save(HERE / "perk_lamp.png")
    vmat(HERE / "perk_lamp.vmat", [
        ("shader", "shaders/complex.shader"), ("F_SELF_ILLUM", "1"), ("TextureColor", "Perks/perk_lamp.png"),
        ("TextureSelfIllumMask", "Perks/perk_lamp.png"), ("g_flSelfIllumBrightness", "3.0"),
        ("g_flSelfIllumAlbedoFactor", "1.0"), ("g_vColorTint", "[1 1 1 1]"), ("g_flModelTintAmount", "1.000"),
        ("g_flMetalness", "0.000"), ("g_bFogEnabled", "1")])

    for key in PERKS:
        label = Image.open(HERE / f"{key}_label.png").convert("RGB")
        poster(key, label).save(HERE / f"{key}_poster.png")
        vmat(HERE / f"{key}_poster.vmat", [
            ("shader", "shaders/simple.shader"), ("TextureColor", f"Perks/{key}_poster.png"),
            ("g_vColorTint", "[1 1 1 1]"), ("g_flModelTintAmount", "1.000"),
            ("g_flMetalness", "0.000"), ("g_flRoughnessScaleFactor", "0.850"), ("g_bFogEnabled", "1")])

        colour, glow = sign(key)
        colour.save(HERE / f"{key}_sign.png")
        glow.save(HERE / f"{key}_sign_glow.png")
        vmat(HERE / f"{key}_sign.vmat", [
            ("shader", "shaders/complex.shader"), ("F_SELF_ILLUM", "1"), ("TextureColor", f"Perks/{key}_sign.png"),
            ("TextureSelfIllumMask", f"Perks/{key}_sign_glow.png"), ("g_flSelfIllumBrightness", "3.0"),
            ("g_flSelfIllumAlbedoFactor", "1.0"), ("g_vColorTint", "[1 1 1 1]"), ("g_flModelTintAmount", "1.000"),
            ("g_flMetalness", "0.000"), ("g_flRoughnessScaleFactor", "0.300"), ("g_bFogEnabled", "1")])

        badge(label).save(UI / f"{key}.png")
    print("perk art written")


if __name__ == "__main__":
    main()
