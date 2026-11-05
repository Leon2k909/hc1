"""Capture the saved replacement, restoring camera, tone, objects and editor state."""
from pathlib import Path
import json,math,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native
OUT=Path(tempfile.gettempdir())/'belltower-sack-pile-v2';native.OUT=OUT
receipt=json.loads((OUT/'install-stage/installed.json').read_text())
s=(HERE/'capture.cs.txt').read_text()
lines=[]
for line in s.splitlines():
    if line.startswith('var candidate='):line='var candidate=false;'
    elif line.startswith('var baseModel='):line='var baseModel=westModel;'
    elif line.startswith('var potModel='):line='var potModel=(Model)null;'
    lines.append(line)
s='\n'.join(lines).replace('sack-pile-v2/capture.cs.txt','sack-pile-v2/capture-installed.cs.txt')+'\n'
helper=HERE/'capture-installed.cs.txt';helper.write_text(s)
position=(805,1130,68);target=(730,1215,20)
x,y,z=[b-a for a,b in zip(position,target)]
angles=(math.degrees(math.atan2(-z,math.hypot(x,y))),math.degrees(math.atan2(y,x)),0)
for name in ('warm-installed','after-installed'):
    config={'directory':'installed','name':name,'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),'width':1280,'height':1024,'fov':48,'exposure':1.5,'settle_ms':0,'candidate':False,'review_fill':True,'expected_scene_sha256':receipt['SourceSceneSha256']}
    (OUT/'capture.json').write_text(json.dumps(config))
    print(name,native.script(helper,name)['Restoration'],flush=True)
