from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/sliding-window-v1';font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
canvas=Image.new('RGB',(1400,1255),(12,16,19));draw=ImageDraw.Draw(canvas)
draw.text((18,12),'Current T2 window',font=font,fill=(229,232,235));draw.text((718,12),'Sliding-window frame — preview',font=font,fill=(229,232,235))
for col,variant in enumerate(('before','after')):
    for row,view in enumerate(('player','base')):
        im=Image.open(OUT/f'native/{view}-{variant}.png').convert('RGB');canvas.paste(im.resize((700,583),Image.Resampling.LANCZOS),(col*700,50+row*595))
draw.text((18,1220),'Same cameras, map lighting and existing window artwork',font=font,fill=(195,201,207));canvas.save(OUT/'comparison.png');print('Saved matched window comparison')
