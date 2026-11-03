"""Before and now, from shots s&box drew before and after the install: python compare.py. Touches nothing in the editor.

The first row is one camera, exactly. Its before was shot with a new desk standing in the next gap, so both are cropped the same to leave that out.
The others are close but not the same camera, and the before shots are a lower resolution, as they come from the candidate survey.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
WORK = os.path.join(ROOT, "output", "asset-improvement-20261030")
DESK = os.path.join(WORK, "spillway-desk")
SURVEY = os.path.join(WORK, "survey", "spillway")
HALF = 896
GAP = 8
FONT = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 26)
ROWS = [
    ((os.path.join(DESK, "engine", "old_front.png"), (0, 0, 1384, 778), "BEFORE"), (os.path.join(DESK, "installed", "desk_front.png"), (0, 0, 1384, 778), "NOW  (same camera)")),
    ((os.path.join(SURVEY, "room_side.png"), None, "BEFORE: THE ROOM"), (os.path.join(DESK, "installed", "room_side.png"), None, "NOW: THE ROOM  (a similar view)")),
    ((os.path.join(SURVEY, "desk_low.png"), None, "BEFORE: FROM THE SIDE"), (os.path.join(DESK, "installed", "desk_side.png"), None, "NOW: FROM THE SIDE  (a similar view)")),
]


def load(path, crop):
    image = Image.open(path).convert("RGB")
    if crop:
        image = image.crop(crop)
    return image.resize((HALF, round(HALF * 9 / 16)), Image.LANCZOS)


height = round(HALF * 9 / 16)
sheet = Image.new("RGB", (HALF * 2 + GAP, (height + GAP) * len(ROWS) - GAP), (0, 0, 0))
draw = ImageDraw.Draw(sheet)
for row, pair in enumerate(ROWS):
    for col, (path, crop, label) in enumerate(pair):
        x, y = col * (HALF + GAP), row * (height + GAP)
        sheet.paste(load(path, crop), (x, y))
        draw.rectangle((x, y, x + draw.textlength(label, font=FONT) + 24, y + 42), fill=(12, 14, 18))
        draw.text((x + 12, y + 6), label, font=FONT, fill=(240, 240, 232))
out = os.path.join(DESK, "before-and-now.png")
sheet.save(out)
print(out, sheet.size)
