from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
OUT=Path(__file__).absolute().parents[3]/'output/ares/control-console-native-v1'
font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',30)
canvas=Image.new('RGB',(1624,1440),'#15191f');d=ImageDraw.Draw(canvas)
for col,label in enumerate(('CURRENT','EXISTING CONSOLE REBUILD — NATIVE PREVIEW')):d.text((col*812+15,12),label,font=font,fill='white')
for row,view in enumerate(('player','detail')):
    for col,variant in enumerate(('before','after')):
        im=Image.open(OUT/f'native/{view}-{variant}.png').convert('RGB');im.thumbnail((800,667));canvas.paste(im,(col*812+6,65+row*685))
canvas.save(OUT/'comparison.png')
