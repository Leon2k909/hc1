"""Update only the gallery material after native visual review."""
from pathlib import Path
import json,hashlib
from native import call,OUT
relative='Assets/materials/ares/floor-finish-v4/grip.vmat'
p=OUT/'stage'/relative;text=p.read_text().replace('g_vColorTint "[1 1 1 1]"','g_vColorTint "[0.65 0.65 0.65 1]"')
p.write_text(text,encoding='utf-8',newline='')
manifest=json.loads((OUT/'manifest.json').read_text());manifest['files'][relative]=hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(call('write_file',dict(path=relative,content=text)))
result=call('asset_compile',dict(path=relative[7:]));assert result.get('Success'),result;print(result)
config=json.loads((OUT/'capture-config.json').read_text());config['variants']=[v for v in config['variants'] if v['name']=='after']
(OUT/'capture-config.json').write_text(json.dumps(config,indent=2))
