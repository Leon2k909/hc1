"""The in-game before and after, side by side: python make_match_sheet.py <shots dir> <out png> <shot names, comma separated>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FOLDER, OUT, NAMES = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
CELL_W, CELL_H, GAP, HEAD, FOOT = 1100, 619, 8, 44, 40
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
W = CELL_W * 2 + GAP
H = HEAD + len(NAMES) * (CELL_H + GAP) - GAP + FOOT
sheet = Image.new("RGB", (W, H), (14, 15, 17))
d = ImageDraw.Draw(sheet)
big = ImageFont.truetype(FONT, 26)
small = ImageFont.truetype(FONT, 18)
d.text((16, 8), "BEFORE: the game today", (235, 235, 235), font=big)
d.text((CELL_W + GAP + 16, 8), "AFTER: new stones in the same places", (235, 235, 235), font=big)
for row, name in enumerate(NAMES):
    y = HEAD + row * (CELL_H + GAP)
    for col, mode in enumerate(("before", "after")):
        frame = Image.open(os.path.join(FOLDER, f"{name}-{mode}.png")).convert("RGB").resize((CELL_W, CELL_H), Image.LANCZOS)
        sheet.paste(frame, (col * (CELL_W + GAP), y))
d.text((16, H - FOOT + 9), "Real in-game screenshots from one Belltower match in s&box, same spot in each row. Not installed: the after uses a temporary copy of the map with the old stones cut out.", (190, 190, 190), font=small)
sheet.save(OUT)
print(OUT, sheet.size)
