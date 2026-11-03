"""The in-engine before/after sheet: python sheet.py <work dir>

The side-by-side across the top, then the same camera before and after, from the renders in <work dir>/engine.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ENGINE = os.path.join(sys.argv[1], "engine")
FONT = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 30)
CELL, GAP = 960, 8


def picture(name, width, crop=None):
    image = Image.open(os.path.join(ENGINE, name + ".png")).convert("RGB")
    if crop:
        image = image.crop(crop)
    return image.resize((width, round(width * image.height / image.width)), Image.LANCZOS)


def label(draw, x, y, text):
    box = draw.textbbox((0, 0), text, font=FONT)
    draw.rectangle((x, y, x + box[2] + 22, y + box[3] + 14), fill=(0, 0, 0))
    draw.text((x + 11, y + 5), text, (240, 240, 240), font=FONT)


wide = 2 * CELL + GAP
top = picture("pair-mixed", wide, crop=(0, 290, 1600, 590))
rows = [("stand", "BEFORE: standing at the bench", "AFTER"), ("three_quarter", "BEFORE", "AFTER")]
cell_h = picture("stand-before", CELL).height
detail = [("downrange-after", "AFTER: from downrange"), ("shelf-after", "AFTER: under the bench")]
height = top.height + GAP + (cell_h + GAP) * (len(rows) + 1) - GAP
sheet = Image.new("RGB", (wide, height), (14, 14, 14))
draw = ImageDraw.Draw(sheet)
sheet.paste(top, (0, 0))
label(draw, 14, 12, "OLD")
label(draw, wide // 2 + 14, 12, "NEW")
y = top.height + GAP
for name, before, after in rows:
    sheet.paste(picture(name + "-before", CELL), (0, y))
    sheet.paste(picture(name + "-after", CELL), (CELL + GAP, y))
    label(draw, 14, y + 12, before)
    label(draw, CELL + GAP + 14, y + 12, after)
    y += cell_h + GAP
for k, (name, text) in enumerate(detail):
    sheet.paste(picture(name, CELL), (k * (CELL + GAP), y))
    label(draw, k * (CELL + GAP) + 14, y + 12, text)
out = os.path.join(sys.argv[1], "bench-before-after-in-sbox.png")
sheet.save(out)
print(out, sheet.size)
