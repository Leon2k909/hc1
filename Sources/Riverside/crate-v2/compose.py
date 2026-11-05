"""Arrange unmodified engine captures for review, with labels explaining the extra light."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(sys.argv[1]).resolve()
OUT = ROOT / "output/asset-improvement-20261030/riverside-crate"
W, H = 750, 500
sheet = Image.new("RGB", (W * 2, H + 96), (20, 22, 23))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 27)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 20)
for k, (variant, title) in enumerate((("old-lit", "ORIGINAL"), ("new-lit", "REWORKED"))):
    shot = Image.open(OUT / (variant + "_close.png")).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    sheet.paste(shot, (k * W, 56))
    draw.text((k * W + W // 2, 28), title, font=font, fill=(230, 231, 230), anchor="mm")
draw.text((W, H + 76), "s&box captures · same map position and camera · temporary inspection light", font=small, fill=(178, 183, 181), anchor="mm")
sheet.save(OUT / "before-after.png")
print(OUT / "before-after.png")
