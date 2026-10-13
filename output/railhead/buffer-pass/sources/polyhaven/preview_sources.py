import json
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

folder = Path(__file__).parent
for name in ['gravel_floor', 'gravel_ground_01', 'rocky_gravel', 'concrete_wall_006', 'metal_plate', 'metal_plate_02', 'blue_metal_plate', 'rusty_metal_04']:
    dest = folder / (name + '.json')
    if not dest.exists():
        request = urllib.request.Request('https://api.polyhaven.com/files/' + name, headers={'User-Agent': 'Railhead-asset-import/1.0'})
        dest.write_bytes(urllib.request.urlopen(request, timeout=25).read())
files = list(folder.glob('*.json'))
sheet = Image.new('RGB', (1024, 1024))
draw = ImageDraw.Draw(sheet)
for i, file in enumerate(files):
    item = json.loads(file.read_text())['Diffuse']['1k']['jpg']
    dest = folder / (file.stem + '_diff.jpg')
    request = urllib.request.Request(item['url'], headers={'User-Agent': 'Railhead-asset-import/1.0'})
    if not dest.exists():
        dest.write_bytes(urllib.request.urlopen(request, timeout=25).read())
    x, y = i % 4 * 256, i // 4 * 256
    sheet.paste(Image.open(dest).resize((256, 230)), (x, y))
    draw.text((x, y + 232), file.stem, fill=(255, 255, 255))
    print(file.stem)
sheet.save(folder / 'selection.png')
