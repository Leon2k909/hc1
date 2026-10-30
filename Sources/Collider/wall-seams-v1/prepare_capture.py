from pathlib import Path
import json

root = Path(__file__).resolve().parents[3]
out = root / 'output/collider-wall-overlap-20261027'
out.mkdir(parents=True, exist_ok=True)
source = (root / 'Sources/Collider/editor/capture.cs.txt').read_text(encoding='utf-8')
source = source.replace('output/collider', 'output/collider-wall-overlap-20261027')
(root / 'Sources/Collider/wall-seams-v1/capture.cs.txt').write_text(source, encoding='utf-8')
config = {'folder':'before', 'width':1400, 'height':900, 'supersample':2, 'views':[
    {'name':'current', 'current':True},
    {'name':'corner-east', 'eye':[1300,430,324], 'target':[1400,650,320], 'fov':72},
    {'name':'corner-west', 'eye':[-1300,430,324], 'target':[-1400,650,320], 'fov':72}
]}
if not (out / 'capture-config.json').exists():
    (out / 'capture-config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
print(out)
