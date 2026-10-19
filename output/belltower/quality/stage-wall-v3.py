from pathlib import Path
import hashlib
import json
import shutil
from PIL import Image

root=Path(__file__).resolve().parents[3]
stage=root/'output/belltower/quality/wall-v3'
stage.mkdir(parents=True,exist_ok=True)
generated=root/'Sources/Belltower/generated'
generated.mkdir(exist_ok=True)
origin=Path('C:/Users/leon2/.codex/generated_images/01a14ff9-008c-7eb3-9076-6b356d896006')
records={
    'wall-limestone-v3-target.png':'exec-e9970455-3279-41b8-9fe5-12bc7c7c536d.png',
    'wall-limestone-v3-color.png':'exec-e48c04f3-9b30-43b6-b796-fc144e0954e8.png',
    'wall-limestone-v3-height.png':'exec-d5de09b1-646b-499f-99ce-5eca11b11e0a.png',
    'ivy-climb-v3.png':'exec-693c554f-9fc9-42ae-b31e-bc413abf91b8.png',
}
result=[]
for name,source in records.items():
    target=generated/name
    if not target.exists():
        shutil.copy2(origin/source,target)
    assert target.read_bytes()==(origin/source).read_bytes()
    image=Image.open(target)
    record={'name':name,'size':image.size,'mode':image.mode,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    if name=='ivy-climb-v3.png':
        assert image.mode=='RGBA'
        alpha=image.getchannel('A')
        record['alpha_range']=alpha.getextrema()
        assert alpha.getextrema()==(0,255)
    result.append(record)
for name in ('Assets/materials/belltower/rubble.vmat','Assets/materials/belltower/ivy_climb.vmat','Tools/belltower_quality_materials.py'):
    target=stage/'before'/name
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/name,target)
(stage/'generated-files.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
helper=(root/'Sources/Belltower/editor/capture-viewport.cs.txt').read_text()
helper=helper.replace('output/belltower/quality/viewport-capture.json','output/belltower/quality/wall-v3/capture.json')
helper=helper.replace('"g_tColor","g_tNormal"','"g_tStoneColor","g_tStoneHeight","g_tColor","g_tNormal"')
(root/'Sources/Belltower/editor/capture-wall-v3.cs.txt').write_text(helper)
exchange=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/a655920748644334b6c97a5d26da3c29')
(exchange/'capture-wall-v3.cs').write_text(helper)
