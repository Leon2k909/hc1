from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/orion/yard-case-reuse-v1'
canvas=Image.new('RGB',(1400,1090),(12,16,19));d=ImageDraw.Draw(canvas);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
d.text((18,12),'Current Orion yard case',font=font,fill=(229,232,235));d.text((718,12),'Existing upgraded case — reused preview',font=font,fill=(229,232,235))
for col,variant in enumerate(('before','after')):
    for row,view in enumerate(('player','close')):
        image=Image.open(OUT/f'native/{view}-{variant}.png').convert('RGB');canvas.paste(image.resize((700,496),Image.Resampling.LANCZOS),(col*700,50+row*510))
d.text((18,1055),'Same location, cameras, map lighting and exposure',font=font,fill=(195,201,207));canvas.save(OUT/'comparison.png');print('Saved matched yard-case comparison')
