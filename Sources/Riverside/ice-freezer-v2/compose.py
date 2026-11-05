"""Arrange native screenshots; no colour or lighting edits."""
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(sys.argv[1]).resolve()
OUT=ROOT/'output/asset-improvement-20261030/riverside-ice-freezer'
canvas=Image.new('RGB',(1800,1430),(20,23,26))
d=ImageDraw.Draw(canvas)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',32)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
d.text((28,20),'LUCKY STOP — ICE FREEZER',font=font,fill='white')
for x,name,label in ((0,'old','ORIGINAL'),(900,'new','REWORKED')):
    d.text((x+28,76),label,font=small,fill=(190,201,210))
    for y,shot in ((116,'angle'),(716,'front')):
        image=Image.open(OUT/(name+'_'+shot+'.png')).convert('RGB')
        image=image.resize((900,600),Image.Resampling.LANCZOS)
        canvas.paste(image,(x,y))
d.text((28,1340),'Native s&box captures • Same cameras and temporary inspection light',font=small,fill=(200,207,212))
d.text((28,1377),'Review candidate • Existing map freezer remains installed',font=small,fill=(157,174,185))
canvas.save(OUT/'before-after.png')
print(OUT/'before-after.png')
