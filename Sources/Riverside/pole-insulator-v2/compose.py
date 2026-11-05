"""Arrange matched native views; no colour or exposure changes."""
from pathlib import Path
import sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/asset-improvement-20261030/riverside-pole-insulator'
canvas=Image.new('RGB',(1800,1560),(20,23,26));d=ImageDraw.Draw(canvas)
title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',32);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
d.text((28,20),'RIVERSIDE — GLAZED POLE INSULATOR',font=title,fill='white')
for x,name,label in ((0,'old','ORIGINAL'),(900,'new','REWORKED')):
    d.text((x+28,76),label,font=font,fill=(190,201,210))
    for y,shot in ((116,'angle'),(776,'detail')):
        im=Image.open(OUT/(name+'_'+shot+'.png')).convert('RGB').resize((900,660),Image.Resampling.LANCZOS);canvas.paste(im,(x,y))
d.text((28,1460),'Native s&box captures • Same cameras, exposure and temporary inspection light',font=font,fill=(200,207,212))
d.text((28,1497),'Existing wire contact and crossarm retained • Review candidate',font=font,fill=(157,174,185))
canvas.save(OUT/'before-after.png');print(OUT/'before-after.png')
