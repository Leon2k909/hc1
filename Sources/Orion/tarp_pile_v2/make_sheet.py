"""The side-by-side sheet from capture_compare's engine shots: python make_sheet.py <project root>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = sys.argv[1]
WORK = os.path.join(ROOT, "output/asset-improvement-20261030/tarp-pile")
ENGINE = os.path.join(WORK, "engine")
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
VIEWS = ["near", "back", "top", "far", "side", "close"]
big = ImageFont.truetype(FONT, 34)
small = ImageFont.truetype(FONT, 20)
rows = [(Image.open(os.path.join(ENGINE, f"{v}-before.png")).convert("RGB"), Image.open(os.path.join(ENGINE, f"{v}-after.png")).convert("RGB")) for v in VIEWS]
width, height = rows[0][0].size
scale = 1000 / width
width, height = 1000, int(height * scale)
gap, head = 10, 104
canvas = Image.new("RGB", (width * 2 + gap, head + len(rows) * (height + gap)), (24, 24, 26))
d = ImageDraw.Draw(canvas)
d.text((14, 10), "Orion tarp pile", (236, 236, 232), font=big)
d.text((14, 52), "Rendered by s&box in Orion's own light, same cameras and held exposure. Off-screen in an isolated scene, not a match, and not installed yet.", (176, 176, 170), font=small)
d.text((14, 78), "BEFORE", (214, 170, 92), font=small)
d.text((width + gap + 14, 78), "AFTER", (120, 200, 140), font=small)
y = head
for left, right in rows:
    canvas.paste(left.resize((width, height), Image.LANCZOS), (0, y))
    canvas.paste(right.resize((width, height), Image.LANCZOS), (width + gap, y))
    y += height + gap
path = os.path.join(WORK, "tarp_pile_before_after.png")
canvas.save(path, optimize=True)
print("wrote", path, canvas.size)
