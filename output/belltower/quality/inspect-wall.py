from pathlib import Path
from PIL import Image
import shutil

root = Path(__file__).resolve().parents[3]
out = root / 'output/belltower/quality/wall-v2'
out.mkdir(exist_ok=True)
exchange = Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/a655920748644334b6c97a5d26da3c29')
shutil.copy2(root / 'Sources/Belltower/editor/capture-viewport.cs.txt', exchange / 'wall-capture.cs')
for path in ('Assets/materials/belltower/rubble.vmat', 'Tools/belltower_map.py', 'Tools/belltower_quality_materials.py', 'Assets/models/maps/belltower/belltower_west.obj', 'Assets/models/maps/belltower/belltower_east.obj'):
    dest = out / 'before-assets' / path
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / path, dest)
for name in ('stone_wall_03', 'medieval_blocks_05', 'medieval_blocks_03'):
    image = Image.open(root / f'Assets/materials/belltower/scans/{name}_diffuse_4k.png')
    image.thumbnail((1000, 1000))
    image.convert('RGB').save(out / f'{name}-preview.jpg', quality=90)

for name, lo, hi in []:
    lines = (root / name).read_text(encoding='utf-8').splitlines()
    print(name)
    for idx in range(lo-1, min(hi, len(lines))):
        print(f'{idx+1}: {lines[idx]}')
