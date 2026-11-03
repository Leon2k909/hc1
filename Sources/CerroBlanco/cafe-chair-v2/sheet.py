"""The before and after sheet from capture_engine.cs.txt's renders: python sheet.py <work folder>

Writes chair-before-after-in-sbox.png beside engine/: one row a view, the scene as it is on the left and with the new chairs on the right.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

WORK = sys.argv[1]
ROWS = [
    ("cafe", "Inside the cafe"),
    ("courtyard", "The courtyard's tables"),
    ("pair", "At a courtyard table"),
    ("close", "Close up"),
    ("seat", "The back slats, close"),
    ("back", "A courtyard chair from behind"),
    ("legs", "Low down"),
]
CELL_W, CELL_H, HEAD, LABEL = 960, 540, 64, 34
font = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 30)
small = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 24)
sheet = Image.new("RGB", (CELL_W * 2, HEAD + len(ROWS) * (CELL_H + LABEL)), (18, 18, 20))
draw = ImageDraw.Draw(sheet)
for column, title in enumerate(("Before: the scene as it is", "After: cafe chair v2")):
    draw.text((column * CELL_W + 20, 16), title, (236, 236, 230), font=font)
for row, (name, caption) in enumerate(ROWS):
    y = HEAD + row * (CELL_H + LABEL)
    draw.text((20, y + 4), caption, (190, 190, 184), font=small)
    for column, variant in enumerate(("before", "after")):
        image = Image.open(os.path.join(WORK, "engine", f"{name}-{variant}.png")).convert("RGB").resize((CELL_W, CELL_H), Image.LANCZOS)
        sheet.paste(image, (column * CELL_W, y + LABEL))
out = os.path.join(WORK, "chair-before-after-in-sbox.png")
sheet.save(out, optimize=True)
print(out)
