"""Side-by-side sheets from the matched renders: python make_sheets.py <render dir> <views>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RENDERS, VIEWS = sys.argv[1], sys.argv[2].split(",")
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
CAPTIONS = {
    "whole": "The whole station",
    "near": "Where a player stands to buy",
    "low": "The feet and brace: the old board hangs in mid-air",
    "lock": "Rail end, padlock and rust from the bolts",
    "rear": "From behind, where a station stands free of a wall",
    "far": "From across a room",
}
for view in VIEWS:
    a = Image.open(os.path.join(RENDERS, f"{view}-before.png")).convert("RGB")
    b = Image.open(os.path.join(RENDERS, f"{view}-after.png")).convert("RGB")
    bar = 54
    gap = 8
    sheet = Image.new("RGB", (a.width + b.width + gap, a.height + bar + 34), (18, 18, 18))
    sheet.paste(a, (0, bar))
    sheet.paste(b, (a.width + gap, bar))
    d = ImageDraw.Draw(sheet)
    big = ImageFont.truetype(FONT, 30)
    small = ImageFont.truetype(FONT, 18)
    d.text((14, 10), "BEFORE: stretched dev box", (235, 235, 235), font=big)
    d.text((a.width + gap + 14, 10), "AFTER: wall-buy board v2", (235, 235, 235), font=big)
    d.text((14, a.height + bar + 6), f"{CAPTIONS[view]}. Blender (Cycles, ACES 1.3) renders of the files, same camera, light and exposure. Not s&box.", (190, 190, 190), font=small)
    sheet.save(os.path.join(RENDERS, f"sheet-{view}.png"))
    print("sheet", view, flush=True)
