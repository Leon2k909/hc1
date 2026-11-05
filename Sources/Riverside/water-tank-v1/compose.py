"""Pair matching native tank renders; resize only."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).absolute().parents[3]/'output/riverside/water-tank-v1'
sheet=Image.new('RGB',(1600,1260),(20,24,27));d=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
d.text((20,12),'RIVERSIDE WATER TOWER - TANK REBUILD',font=font,fill=(231,234,225))
for i,version in enumerate(('before','after')):
    x=i*800;d.text((x+20,55),version.upper(),font=font,fill=(221,210,172))
    a=Image.open(OUT/f'overview-{version}.png').convert('RGB').resize((800,600),Image.Resampling.LANCZOS);sheet.paste(a,(x,98))
    a=Image.open(OUT/'context'/f'tank-{version}.png').convert('RGB').resize((800,525),Image.Resampling.LANCZOS);sheet.paste(a,(x,735))
d.text((20,704),'Bottom: original tower, lettering and map lights. Matching cameras and exposure.',font=small,fill=(218,223,216))
sheet.save(OUT/'comparison.png');print(OUT/'comparison.png')
