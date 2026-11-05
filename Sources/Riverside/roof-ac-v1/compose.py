"""Lay out the unaltered native before/after captures."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).absolute().parents[3]
OUT=ROOT/'output/riverside/roof-ac-v1'
sheet=Image.new('RGB',(1600,1245),(21,25,27));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',25)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
draw.text((20,14),'OFFICE ROOFTOP AIR CONDITIONER — s&box engine comparison',font=font,fill=(232,232,218))
for col,variant in enumerate(('before','after')):
    x=col*800
    draw.text((x+20,56),variant.upper(),font=font,fill=(223,209,163))
    im=Image.open(OUT/f'three-quarter-{variant}.png').convert('RGB').resize((800,640),Image.Resampling.LANCZOS)
    sheet.paste(im,(x,94))
    im=Image.open(OUT/'context'/f'close-{variant}.png').convert('RGB').resize((800,525),Image.Resampling.LANCZOS)
    sheet.paste(im,(x,720))
draw.text((20,686),'Same camera and lighting on each side. Bottom: the office roof under Riverside’s own light.',font=small,fill=(217,220,218))
sheet.save(OUT/'comparison.png')
print(OUT/'comparison.png')
