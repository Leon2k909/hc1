"""Prepare private, state-restoring native views; no installed assets are written."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/collider-ceiling-v1-20261027'
OUT.mkdir(parents=True, exist_ok=True)
source = (ROOT / 'Sources/Collider/editor/capture.cs.txt').read_text(encoding='utf-8')
source = source.replace('output/collider', 'output/collider-ceiling-v1-20261027')
# Include private ceiling textures in the same source-change guards as the
# established screenshot helper. Before installation the directory is absent.
source=source.replace('System.IO.Directory.EnumerateFiles(System.IO.Path.Combine(root,"Assets/materials/collider/craft-v1"))',
    'new[]{"craft-v1","ceiling-v1"}.SelectMany(surfaceFolder=>System.IO.Directory.Exists(System.IO.Path.Combine(root,"Assets/materials/collider",surfaceFolder)) ? System.IO.Directory.EnumerateFiles(System.IO.Path.Combine(root,"Assets/materials/collider",surfaceFolder)) : Array.Empty<string>())')
(ROOT / 'Sources/Collider/ceiling-v1/capture.cs.txt').write_text(source, encoding='utf-8')
config = {'folder':'before', 'width':1500, 'height':1000, 'supersample':2, 'views':[
    {'name':'ceiling', 'eye':[150,-320,640], 'target':[150,120,900], 'fov':90},
    {'name':'fixture', 'eye':[260,-485,798], 'target':[300,-420,846], 'fov':65},
    {'name':'hall', 'eye':[850,-620,330], 'target':[-650,500,440], 'fov':82}
]}
if not (OUT / 'capture-config.json').exists():
    (OUT / 'capture-config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
print(OUT)
