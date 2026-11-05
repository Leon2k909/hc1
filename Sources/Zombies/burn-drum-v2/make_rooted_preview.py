"""Compose unaltered native capture frames into a small motion preview and contact sheet."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).absolute().parents[3]
WORK = ROOT / 'output/riverside/drum-fire-rooted'
paths = sorted((WORK/'after').glob('motion-*.png'))
frames = [Image.open(p).convert('RGB').crop((500,180,1040,720)).resize((540,540),Image.Resampling.LANCZOS) for p in paths]
palette_source = Image.new('RGB',(540*4,540*4))
for i, f in enumerate(frames[::6][:16]):
    palette_source.paste(f,((i%4)*540,(i//4)*540))
palette = palette_source.quantize(colors=256)
indexed = [f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
indexed[0].save(WORK/'fire-motion.gif',save_all=True,append_images=indexed[1:],duration=32,loop=0,optimize=True)
sheet = Image.new('RGB',(540*4,540*2+64),(24,24,24))
draw=ImageDraw.Draw(sheet)
for i, index in enumerate((0,12,24,36,48,60,72,84)):
    sheet.paste(frames[index],((i%4)*540,(i//4)*(540+32)+32))
    draw.text(((i%4)*540+12,(i//4)*(540+32)+8),f'{index*0.032:.2f} s',fill='white')
sheet.save(WORK/'motion-contact.png')
print(WORK/'fire-motion.gif')
