from pathlib import Path
import json

root=Path(__file__).resolve().parents[3]
out=root/'output/collider-server-rack-20261027'
out.mkdir(parents=True,exist_ok=True)
capture=(root/'Sources/Collider/editor/capture.cs.txt').read_text()
capture=capture.replace('output/collider','output/collider-server-rack-20261027')
capture=capture.replace('new[]{"collider_structure","collider_machine"}','new[]{"collider_structure","collider_machine","collider_detail"}')
(root/'Sources/Collider/server-rack-v1/capture.cs.txt').write_text(capture)
config={'folder':'before','width':1500,'height':950,'supersample':2,'views':[
    {'name':'stair','eye':[290,-150,105],'target':[520,90,52],'fov':76},
    {'name':'rack','eye':[345,-188,68],'target':[430,-60,44],'fov':63}]}
if not (out/'capture-config.json').exists():
    (out/'capture-config.json').write_text(json.dumps(config,indent=2))
(out/'compile-args.json').write_text(json.dumps({'path':'models/maps/collider/collider_detail.vmdl','full':False}))
print('Prepared native rack capture and compile inputs')
