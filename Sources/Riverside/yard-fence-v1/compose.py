from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import io
OUT=Path(__file__).absolute().parents[3]/'output/riverside/yard-fence-v1'
sheet=Image.new('RGB',(1600,1190),(20,24,27));d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
d.text((20,12),'RIVERSIDE WEST YARD - TIMBER PRIVACY FENCE',font=small,fill=(230,233,224))
for i,v in enumerate(('before','after')):
 x=i*800;d.text((x+20,53),v.upper(),font=font,fill=(222,210,170))
 for j,view in enumerate(('whole','detail')):
  a=Image.open(OUT/'context'/f'{view}-{v}.png').convert('RGB').resize((800,525),Image.Resampling.LANCZOS);sheet.paste(a,(x,94+j*530))
d.text((20,1160),'Matching standing-height cameras, map light and exposure. Preview only.',font=small,fill=(218,222,215))
b=io.BytesIO();sheet.save(b,format='PNG');(OUT/'comparison.png').write_bytes(b.getvalue());print(OUT/'comparison.png')
