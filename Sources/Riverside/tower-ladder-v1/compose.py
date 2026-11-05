"""Pair matching engine views of the old and fitted approved ladder design."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import io
OUT=Path(__file__).absolute().parents[3]/'output/riverside/tower-ladder-v1'
sheet=Image.new('RGB',(1600,1260),(20,24,27));d=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
d.text((18,12),'GUARD-TOWER LADDER - APPROVED LOWTIDE DESIGN FITTED TO RIVERSIDE',font=small,fill=(231,234,225))
for i,version in enumerate(('before','after')):
    x=i*800;d.text((x+18,55),version.upper(),font=font,fill=(222,210,170))
    a=Image.open(OUT/f'detail-{version}.png').convert('RGB').resize((800,600),Image.Resampling.LANCZOS);sheet.paste(a,(x,98))
    a=Image.open(OUT/'context'/f'tower-{version}.png').convert('RGB').resize((800,525),Image.Resampling.LANCZOS);sheet.paste(a,(x,735))
d.text((18,704),'Bottom: same tower, camera, map lighting and exposure. Preview only.',font=small,fill=(218,222,215))
b=io.BytesIO();sheet.save(b,format='PNG');(OUT/'comparison.png').write_bytes(b.getvalue());print(OUT/'comparison.png')
