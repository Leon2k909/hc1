"""Lay out unaltered engine captures for review. python sheets.py"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).absolute().parents[3]
folder = root / 'output/asset-improvement-20261030/spillway-hose/matched'
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 25)
small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
width = 1000
height = round(860 * width / 1400)
sheet = Image.new('RGB', (width * 2, 68 + (height + 42) * 2), (23, 25, 25))
draw = ImageDraw.Draw(sheet)
draw.text((20, 15), 'BEFORE / three closed rings', fill=(224, 224, 215), font=font)
draw.text((width + 20, 15), 'AFTER / continuous hose and hollow couplings', fill=(224, 224, 215), font=font)
for row, (camera, caption) in enumerate([('standing', 'Standing view / same camera and exposure'), ('above', 'Above / the route of one continuous hose')]):
    y = 68 + row * (height + 42)
    for col, setup in enumerate(('before', 'after')):
        image = Image.open(folder / f'{setup}_{camera}.png').convert('RGB')
        sheet.paste(image.resize((width, height), Image.Resampling.LANCZOS), (col * width, y))
    draw.text((20, y + height + 7), caption, fill=(185, 187, 176), font=small)
sheet.save(folder / 'comparison.png')
print(folder / 'comparison.png')
