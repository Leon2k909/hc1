"""Compare unaltered native barrel-fire captures, cropped equally around the drum."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).absolute().parents[3]
work = root / 'output/riverside' / (sys.argv[1] if len(sys.argv)>1 else 'drum-fire-fit')
crop = (450,20,1110,1024)
w, h = crop[2]-crop[0], crop[3]-crop[1]
sheet = Image.new('RGB',(w*2,h+48),(22,24,24))
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',24)
for k,(folder,label) in enumerate([('before','BEFORE'),('after','AFTER')]):
    shot = Image.open(work / folder / 'front-after.png').convert('RGB')
    sheet.paste(shot.crop(crop),(k*w,48))
    draw.text((k*w+18,9),label,font=font,fill=(226,227,218))
sheet.save(work / 'comparison.png')
print(work / 'comparison.png')
