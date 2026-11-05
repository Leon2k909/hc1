from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import io
OUT=Path(__file__).absolute().parents[3]/'output/riverside/interior-fridges-v1'
sheet=Image.new('RGB',(1600,654),(20,24,27));d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
d.text((20,12),'LUCKY STOP INTERIOR FRIDGES - APPROVED CABINET DESIGN REUSED',font=small,fill=(230,233,224))
for i,v in enumerate(('before','after')):
 x=i*800;d.text((x+20,53),v.upper(),font=font,fill=(222,210,170))
 for j,view in enumerate(('aisle',)):
  a=Image.open(OUT/'context'/f'{view}-{v}.png').convert('RGB').resize((800,525),Image.Resampling.LANCZOS);sheet.paste(a,(x,94+j*530))
d.text((20,628),'Matching player-height cameras, map lighting and exposure. Preview only.',font=small,fill=(218,222,215))
b=io.BytesIO();sheet.save(b,format='PNG');(OUT/'player-height-comparison.png').write_bytes(b.getvalue());print(OUT/'player-height-comparison.png')
