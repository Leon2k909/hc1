"""One labelled image of the two paints: python sheet_scan_compare.py <work dir>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

WORK = sys.argv[1]
SHOTS = os.path.join(WORK, "blender")
FONT = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 28)
SMALL = ImageFont.truetype(r"C:\Windows\Fonts\bahnschrift.ttf", 22)
whole = Image.open(os.path.join(SHOTS, "compare_whole.png")).convert("RGB")
now = Image.open(os.path.join(SHOTS, "compare_close_now.png")).convert("RGB")
scans = Image.open(os.path.join(SHOTS, "compare_close_scans.png")).convert("RGB")
GAP = 8
width = whole.width
close_w = (width - GAP) // 2
close_h = round(close_w * now.height / now.width)
now = now.resize((close_w, close_h), Image.LANCZOS)
scans = scans.resize((close_w, close_h), Image.LANCZOS)
sheet = Image.new("RGB", (width, whole.height + GAP + close_h + 44), (14, 14, 14))
draw = ImageDraw.Draw(sheet)
sheet.paste(whole, (0, 0))
sheet.paste(now, (0, whole.height + GAP))
sheet.paste(scans, (close_w + GAP, whole.height + GAP))


def label(x, y, text):
    box = draw.textbbox((0, 0), text, font=FONT)
    draw.rectangle((x, y, x + box[2] + 22, y + box[3] + 14), fill=(0, 0, 0))
    draw.text((x + 11, y + 5), text, (240, 240, 240), font=FONT)


label(14, 12, "INSTALLED NOW: paint made by code")
label(width // 2 + 14, 12, "TRIAL: paint from real metal photo scans")
label(14, whole.height + GAP + 12, "INSTALLED NOW, up close")
label(close_w + GAP + 14, whole.height + GAP + 12, "TRIAL, up close")
draw.text((14, sheet.height - 34), "Blender renders, not s&box: this shows how the two paints differ, not how either looks in the game.", (190, 190, 190), font=SMALL)
out = os.path.join(WORK, "first-aid-paint-compare.png")
sheet.save(out)
print(out, sheet.size)
