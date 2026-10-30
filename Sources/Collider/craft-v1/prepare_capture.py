from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider-detail-v3-20261027'
source=(ROOT/'Sources/Collider/editor/capture.cs.txt').read_text(encoding='utf-8')
source=source.replace('output/collider','output/collider-detail-v3-20261027')
assert 'Supersampling=scale' in source and 'AssetSourcesSHA256=inputHashes' in source
(ROOT/'Sources/Collider/craft-v1/capture.cs.txt').write_text(source,encoding='utf-8')
config={'width':1864,'height':916,'supersample':2,'views':[
    {'name':'viewport-before','current':True},
    {'name':'rail-before','eye':[-1120,-380,316],'target':[-930,-100,284],'fov':75},
    {'name':'floor-before','eye':[-750,-360,68],'target':[-960,-410,0],'fov':75}]}
OUT.mkdir(parents=True,exist_ok=True)
if not (OUT/'capture-config.json').exists():
    (OUT/'capture-config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
print('Prepared persistent-camera capture: native 3728x1832 to 1864x916, original pose/projection restored.')
