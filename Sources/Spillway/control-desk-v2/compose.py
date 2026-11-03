"""The before and after sheet, from the engine's own renders: python compose.py <engine folder> <out png>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

folder, out = sys.argv[1], sys.argv[2]
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
WIDTH = 1800
GAP = 8
BAND = 46


def load(name, w, crop=None):
    im = Image.open(os.path.join(folder, name + ".png")).convert("RGB")
    if crop:
        im = im.crop(crop)
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def label(canvas, x, y, text):
    d = ImageDraw.Draw(canvas)
    d.rectangle((x, y, x + d.textlength(text, font=F) + 28, y + BAND), fill=(12, 14, 18))
    d.text((x + 14, y + 8), text, font=F, fill=(240, 240, 232))


F = ImageFont.truetype(FONT, 28)
half = (WIDTH - GAP) // 2
rows = [
    [("pair", WIDTH, (60, 100, 1540, 780), "IN S&BOX, SAME ROOM AND LIGHT:  NEW ON THE LEFT, OLD ON THE RIGHT")],
    [("old_front", half, None, "BEFORE"), ("new_front", half, None, "AFTER  (same camera)")],
    [("new_side", half, None, "AFTER"), ("board_close", half, None, "AFTER, CLOSE UP")],
]
images = [[(load(n, w, c), t) for n, w, c, t in row] for row in rows]
height = sum(max(im.height for im, _ in row) + GAP for row in images) - GAP
sheet = Image.new("RGB", (WIDTH, height), (0, 0, 0))
y = 0
for row in images:
    x = 0
    for im, text in row:
        sheet.paste(im, (x, y))
        label(sheet, x, y, text)
        x += im.width + GAP
    y += max(im.height for im, _ in row) + GAP
sheet.save(out)
print(sheet.size)
