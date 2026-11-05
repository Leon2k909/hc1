"""Arrange native captures without altering their image pixels."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/riverside/neon-sign-v1'
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',28)
for shot in ('whole','detail','rear'):
    images=[Image.open(OUT/f'{variant}_{shot}.png').convert('RGB') for variant in ('old','new')]
    w,h=images[0].size;canvas=Image.new('RGB',(w,h*2+100),(20,22,25));draw=ImageDraw.Draw(canvas)
    for i,(label,im) in enumerate(zip(('BEFORE','AFTER'),images)):
        y=i*(h+50);draw.text((22,y+5),label,font=font,fill=(235,237,240));canvas.paste(im,(0,y+50))
    canvas.save(OUT/f'compare_{shot}.png',compress_level=2)
print(OUT/'compare_whole.png')
