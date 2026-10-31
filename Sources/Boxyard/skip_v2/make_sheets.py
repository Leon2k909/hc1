"""Side-by-side sheets from the renders: python make_sheets.py <renders dir> <out dir> <sheet name> <view,view,...>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RENDERS, OUT, NAME = sys.argv[1], sys.argv[2], sys.argv[3]
VIEWS = sys.argv[4].split(",")
os.makedirs(OUT, exist_ok=True)
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
pairs = [(Image.open(os.path.join(RENDERS, f"{v}-before.png")).convert("RGB"), Image.open(os.path.join(RENDERS, f"{v}-after.png")).convert("RGB")) for v in VIEWS]
w = max(a.width for a, _ in pairs)
gap, head, foot = 8, 44, 34
h = sum(a.height for a, _ in pairs) + gap * (len(pairs) - 1)
sheet = Image.new("RGB", (w * 2 + gap, h + head + foot), (16, 16, 18))
d = ImageDraw.Draw(sheet)
f = ImageFont.truetype(FONT, 26)
d.text((16, 8), "BEFORE: shipped skip", (214, 214, 214), font=f)
d.text((w + gap + 16, 8), "AFTER: v2 candidate (not in the game)", (214, 214, 214), font=f)
y = head
for a, b in pairs:
    sheet.paste(a, (0, y))
    sheet.paste(b, (w + gap, y))
    y += a.height + gap
small = ImageFont.truetype(FONT, 18)
d.text((16, h + head + 7), "Blender Cycles renders of the exported files: same camera, light, exposure, ACES 1.3. Not s&box screenshots.", (150, 150, 150), font=small)
path = os.path.join(OUT, f"{NAME}.png")
sheet.save(path, compress_level=6)
print(path, sheet.size)
