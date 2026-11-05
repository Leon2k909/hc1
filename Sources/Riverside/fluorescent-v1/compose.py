"""Compose matching native render pairs without changing their colors."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).absolute().parents[3]/'output/riverside/fluorescent-v1'
sheet=Image.new('RGB',(1600,1092),(21,25,27));d=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',26)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
d.text((18,12),'LUCKY STOP FLUORESCENT FIXTURE — s&box engine comparison',font=font,fill=(230,232,219))
for i,version in enumerate(('before','after')):
    x=i*800;d.text((x+18,53),version.upper(),font=font,fill=(223,209,163))
    a=Image.open(OUT/f'overview-{version}.png').convert('RGB').resize((800,467),Image.Resampling.LANCZOS)
    sheet.paste(a,(x,92))
    a=Image.open(OUT/'context'/f'close-{version}.png').convert('RGB').resize((800,525),Image.Resampling.LANCZOS)
    sheet.paste(a,(x,567))
d.text((18,536),'Bottom: under the store’s own lights. Same cameras and exposure on both sides.',font=small,fill=(218,221,216))
sheet.save(OUT/'comparison.png');print(OUT/'comparison.png')
