"""Before-and-after sheets from render_device.py's images: python make_sheets.py <render dir> <out dir> <sheet name=view,view> ..."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RENDERS, OUT = sys.argv[1], sys.argv[2]
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
TITLES = {
    "hero": "Three-quarter",
    "hands": "Operator's side (my estimate, not the game's camera)",
    "top": "From above",
    "keys": "Close on the keypad",
    "side": "From the side",
    "rear": "From behind",
}
GAP = 8
os.makedirs(OUT, exist_ok=True)
for arg in sys.argv[3:]:
    name, views = arg.split("=")
    rows = []
    for view in views.split(","):
        before = Image.open(os.path.join(RENDERS, f"{view}-before.png")).convert("RGB")
        after = Image.open(os.path.join(RENDERS, f"{view}-after.png")).convert("RGB")
        rows.append((view, before, after))
    w = rows[0][1].width * 2 + GAP
    label = 44
    h = sum(r[1].height + label for r in rows) + 60
    sheet = Image.new("RGB", (w, h), (18, 18, 19))
    d = ImageDraw.Draw(sheet)
    big = ImageFont.truetype(FONT, 26)
    small = ImageFont.truetype(FONT, 20)
    y = 0
    for view, before, after in rows:
        d.text((12, y + 9), "BEFORE: " + TITLES[view], (198, 198, 192), font=big)
        d.text((before.width + GAP + 12, y + 9), "AFTER: " + TITLES[view], (232, 200, 150), font=big)
        y += label
        sheet.paste(before, (0, y))
        sheet.paste(after, (before.width + GAP, y))
        y += before.height
    d.text((12, y + 18), "Blender Cycles renders with matched camera, light and exposure (ACES 1.3). Not compiled or seen in s&box.", (150, 150, 146), font=small)
    sheet.save(os.path.join(OUT, f"{name}.png"))
    print("sheet", name, sheet.size, flush=True)
