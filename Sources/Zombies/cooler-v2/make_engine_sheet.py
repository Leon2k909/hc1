"""Side-by-side sheet of the engine capture: python make_engine_sheet.py <engine dir>"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ENGINE = sys.argv[1]
FONT = r"C:\Windows\Fonts\bahnschrift.ttf"
a = Image.open(os.path.join(ENGINE, "front-before.png")).convert("RGB")
b = Image.open(os.path.join(ENGINE, "front-after.png")).convert("RGB")
scale = 860 / a.width
a = a.resize((860, int(a.height * scale)), Image.LANCZOS)
b = b.resize((860, int(b.height * scale)), Image.LANCZOS)
bar = 54
gap = 8
sheet = Image.new("RGB", (a.width + b.width + gap, a.height + bar + 34), (18, 18, 18))
sheet.paste(a, (0, bar))
sheet.paste(b, (a.width + gap, bar))
d = ImageDraw.Draw(sheet)
d.text((14, 10), "BEFORE: Riverside's cooler", (235, 235, 235), font=ImageFont.truetype(FONT, 30))
d.text((a.width + gap + 14, 10), "AFTER: cooler v2", (235, 235, 235), font=ImageFont.truetype(FONT, 30))
d.text((14, a.height + bar + 6), "Rendered by s&box in Riverside's own light, same camera, exposure held at the map's ceiling of 3.5. An editor capture, not a live match.", (190, 190, 190), font=ImageFont.truetype(FONT, 18))
sheet.save(os.path.join(ENGINE, "sheet-front.png"))
print("sheet written", flush=True)
