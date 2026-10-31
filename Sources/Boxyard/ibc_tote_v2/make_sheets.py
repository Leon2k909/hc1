"""The side-by-side sheet from render_tote.py's images: python make_sheets.py <renders dir> <out dir>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RENDERS, OUT = sys.argv[1], sys.argv[2]
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
VIEWS = ["hero", "side", "valve", "top", "far"]
NOTE = "Blender Cycles renders, same camera, light and exposure, ACES 1.3. Not compiled or seen in s&box, and not in the game yet. Old tote from the map's own generator, on its real materials."
big = ImageFont.truetype(FONT, 34)
small = ImageFont.truetype(FONT, 20)
rows = []
for view in VIEWS:
    a, b = os.path.join(RENDERS, f"{view}-before.png"), os.path.join(RENDERS, f"{view}-after.png")
    if not (os.path.exists(a) and os.path.exists(b)):
        print("skipping", view)
        continue
    left, right = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if view == "far":
        # A crop of 1080p at a 60 degree view from 8 metres, doubled with no smoothing so the pixels show.
        left = left.resize((left.width * 2, left.height * 2), Image.NEAREST)
        right = right.resize((right.width * 2, right.height * 2), Image.NEAREST)
    rows.append((view, left, right))
width = max(r[1].width for r in rows)
gap, head = 10, 104
canvas = Image.new("RGB", (width * 2 + gap, head + sum(r[1].height + gap for r in rows)), (24, 24, 26))
d = ImageDraw.Draw(canvas)
d.text((14, 10), "Boxyard IBC tote", (236, 236, 232), font=big)
d.text((14, 52), NOTE, (176, 176, 170), font=small)
d.text((14, 78), "BEFORE", (214, 170, 92), font=small)
d.text((width + gap + 14, 78), "AFTER", (120, 200, 140), font=small)
y = head
for view, left, right in rows:
    canvas.paste(left, ((width - left.width) // 2, y))
    canvas.paste(right, (width + gap + (width - right.width) // 2, y))
    if view == "far":
        d.text((14, y + 8), "8 m away, 1080p, doubled", (236, 236, 232), font=small)
    y += left.height + gap
path = os.path.join(OUT, "ibc_tote_before_after.png")
canvas.save(path, optimize=True)
print("wrote", path, canvas.size)
