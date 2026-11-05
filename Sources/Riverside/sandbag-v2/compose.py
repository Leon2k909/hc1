"""Label and arrange matched engine captures without changing their colours or lighting."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "output/asset-improvement-20261030/riverside-sandbags"
W = 750
WALL_H, DETAIL_H, HEAD, GAP, FOOT = 212, 475, 56, 12, 40
sheet = Image.new("RGB", (W * 2, HEAD + WALL_H + GAP + DETAIL_H + FOOT), (19, 21, 22))
d = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 27)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 19)
for k, (variant, title) in enumerate((("old", "ORIGINAL"), ("new", "REWORKED"))):
    wall = Image.open(OUT / (variant + "_wall.png")).convert("RGB").crop((70, 300, 1450, 690)).resize((W, WALL_H), Image.Resampling.LANCZOS)
    detail = Image.open(OUT / (variant + "_detail.png")).convert("RGB").resize((W, DETAIL_H), Image.Resampling.LANCZOS)
    sheet.paste(wall, (k * W, HEAD))
    sheet.paste(detail, (k * W, HEAD + WALL_H + GAP))
    d.text((k * W + W // 2, HEAD // 2), title, font=font, fill=(232, 232, 230), anchor="mm")
d.text((W, sheet.height - FOOT // 2), "s&box captures · matched cameras and placement · temporary inspection light", font=small, fill=(180, 183, 181), anchor="mm")
sheet.save(OUT / "before-after.png")
print(OUT / "before-after.png")
