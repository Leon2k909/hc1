from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/reefhall/display-coral-v1';font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
canvas=Image.new('RGB',(1400,1255),(12,16,19));draw=ImageDraw.Draw(canvas)
draw.text((18,12),'Current display coral',font=font,fill=(229,232,235));draw.text((718,12),'Curved branching coral — preview',font=font,fill=(229,232,235))
for col,variant in enumerate(('before','after')):
    for row,view in enumerate(('player','base')):
        im=Image.open(OUT/f'native/{view}-{variant}.png').convert('RGB');canvas.paste(im.resize((700,583),Image.Resampling.LANCZOS),(col*700,50+row*595))
draw.text((18,1220),'Same cameras and aquarium lighting; installed pedestal in both',font=font,fill=(195,201,207));canvas.save(OUT/'comparison.png');print('Saved matched coral comparison')
