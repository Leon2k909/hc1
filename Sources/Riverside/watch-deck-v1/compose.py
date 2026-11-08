"""Put each matched before/after pair of editor viewport captures side by side (comparison-N.png).

The captures are the editor's own viewport, cropped, from the same camera pose each time (poses in README.md), with the
editor's light gizmos in both. Nothing is retouched.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

OUT = Path(__file__).absolute().parents[3] / 'output/riverside/watch-deck-v1'
TITLES = {1: 'from the south-east, standing height', 2: 'straight up the stair', 3: 'from the west, standing height'}
bold = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 30)
small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
for n in (1, 2, 3):
    a = Image.open(OUT / f'before-{n}.png').convert('RGB')
    b = Image.open(OUT / f'after-{n}.png').convert('RGB')
    assert a.size == b.size
    w, h = a.size
    sheet = Image.new('RGB', (w * 2 + 12, h + 92), (20, 24, 27))
    d = ImageDraw.Draw(sheet)
    d.text((16, 10), 'RIVERSIDE SPAWN-PAD WATCH DECK - ' + TITLES[n].upper(), font=small, fill=(230, 233, 224))
    d.text((16, 44), 'BEFORE', font=bold, fill=(222, 210, 170))
    d.text((w + 28, 44), 'AFTER', font=bold, fill=(222, 210, 170))
    sheet.paste(a, (0, 92))
    sheet.paste(b, (w + 12, 92))
    buf = io.BytesIO()
    sheet.save(buf, format='PNG')
    (OUT / f'comparison-{n}.png').write_bytes(buf.getvalue())
    print(OUT / f'comparison-{n}.png', sheet.size)
