"""Cerro Blanco's extinguishers before and after on one sheet: python make_sheet.py <shots dir> <out png> <footer>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FOLDER, OUT, FOOTER = sys.argv[1:4]
NAMES = ("beside-a-painting", "from-eye-height", "in-the-room")
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
W, H, GAP, HEAD, FOOT = 1100, 688, 8, 44, 40
sheet = Image.new("RGB", (W * 2 + GAP, HEAD + len(NAMES) * (H + GAP) - GAP + FOOT), (14, 15, 17))
d = ImageDraw.Draw(sheet)
d.text((16, 8), "BEFORE", (235, 235, 235), font=ImageFont.truetype(FONT, 26))
d.text((W + GAP + 16, 8), "AFTER: Railhead's extinguisher", (235, 235, 235), font=ImageFont.truetype(FONT, 26))
for row, name in enumerate(NAMES):
    for col, mode in enumerate(("before", "after")):
        frame = Image.open(os.path.join(FOLDER, f"{name}-{mode}.png")).convert("RGB").resize((W, H), Image.LANCZOS)
        sheet.paste(frame, (col * (W + GAP), HEAD + row * (H + GAP)))
d.text((16, sheet.height - FOOT + 9), FOOTER, (190, 190, 190), font=ImageFont.truetype(FONT, 18))
sheet.save(OUT)
print(OUT, sheet.size)
