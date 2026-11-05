"""Lay out the unaltered engine screenshots for review."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).absolute().parents[3]
folder = root / 'output/asset-improvement-20261030/spillway-vent/matched'
width, title, gap = 1000, 64, 40
height = round(width * 860 / 1400)
sheet = Image.new('RGB', (width * 2, title + (height + gap) * 2), (23, 25, 25))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 25)
small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
draw.text((20, 16), 'BEFORE / turbine hall wall vent', font=font, fill=(225, 225, 218))
draw.text((width + 20, 16), 'AFTER / folded blades, service frame and rain cap', font=font, fill=(225, 225, 218))
for row, (camera, label) in enumerate([('standing', 'Same camera, lighting and exposure'), ('low', 'Lower view / blade depth and wall projection')]):
    y = title + row * (height + gap)
    for col, setup in enumerate(('before', 'after')):
        shot = Image.open(folder / f'{setup}_{camera}.png').convert('RGB')
        sheet.paste(shot.resize((width, height), Image.Resampling.LANCZOS), (col * width, y))
    draw.text((20, y + height + 6), label, font=small, fill=(183, 187, 177))
sheet.save(folder / 'comparison.png')
print(folder / 'comparison.png')
