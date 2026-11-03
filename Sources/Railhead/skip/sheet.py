"""The skip's before/after from the engine renders: python sheet.py <work dir>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

WORK = sys.argv[1]
SURVEY = os.path.join(WORK, "survey")
FONT = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 28)
CELL, GAP = 960, 8
CELLS = [("railhead_a", "BEFORE: Railhead's skip"), ("after_a", "AFTER: Lowtide's skip, same spot"), ("after_west", "AFTER: the west side"), ("after_b", "AFTER: from the other end")]
pictures = [Image.open(os.path.join(SURVEY, name + ".png")).convert("RGB") for name, _ in CELLS]
pictures = [p.resize((CELL, round(CELL * p.height / p.width)), Image.LANCZOS) for p in pictures]
h = pictures[0].height
sheet = Image.new("RGB", (2 * CELL + GAP, 2 * h + GAP), (14, 14, 14))
draw = ImageDraw.Draw(sheet)
for k, (picture, (_, text)) in enumerate(zip(pictures, CELLS)):
    x, y = (k % 2) * (CELL + GAP), (k // 2) * (h + GAP)
    sheet.paste(picture, (x, y))
    box = draw.textbbox((0, 0), text, font=FONT)
    draw.rectangle((x + 14, y + 12, x + 36 + box[2], y + 26 + box[3]), fill=(0, 0, 0))
    draw.text((x + 25, y + 17), text, (240, 240, 240), font=FONT)
out = os.path.join(WORK, "skip-before-after-in-sbox.png")
sheet.save(out)
print(out, sheet.size)
