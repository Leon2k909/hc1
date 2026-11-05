"""Matched native renders; only identical crop/resizing and labels are applied."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/orion/radome-v1'
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
canvas=Image.new('RGB',(1400,1280),(12,16,19));draw=ImageDraw.Draw(canvas)
draw.text((22,14),'Current Orion radome',font=font,fill=(228,232,234))
draw.text((722,14),'Rebuilt radome — preview',font=font,fill=(228,232,234))
for col,variant in enumerate(('before','after')):
    image=Image.open(OUT/f'studio/whole-{variant}.png').convert('RGB')
    canvas.paste(image.resize((700,642),Image.Resampling.LANCZOS),(col*700,55))
    image=Image.open(OUT/f'studio/structure-{variant}.png').convert('RGB')
    canvas.paste(image.crop((0,230,1200,1100)).resize((700,507),Image.Resampling.LANCZOS),(col*700,730))
draw.text((22,1240),'Same cameras, lighting and exposure in both columns',font=font,fill=(200,205,210))
canvas.save(OUT/'comparison.png');print('Saved radome comparison')
