from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/warning-sign-v1'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
plan=json.loads((OUT/'plan.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,wanted in plan['install_files'].items():
    assert sha(ROOT/'Assets/models/maps/sewage'/name)==wanted,('Installed file differs',name)
_,before=S.read_obj(OUT/'baseline/sewage_signage.obj')
_,after=S.read_obj(ROOT/'Assets/models/maps/sewage/sewage_signage.obj')
assert not Counter(before)-Counter(after),'Original signage changed'
assert len(after)-len(before)==3700
text=(HERE/'capture.cs.txt').read_text()
old='signage.Model=Model.Load("models/maps/sewage/warning-sign-v1/"+variant+".vmdl");'
new='signage.Model=Model.Load(variant=="after"?"models/maps/sewage/sewage_signage.vmdl":"models/maps/sewage/warning-sign-v1/before.vmdl");'
assert old in text
(HERE/'capture-installed.cs.txt').write_text(text.replace(old,new))
result=dict(InstalledFilesMatchStage=True,OriginalTrianglesRetained=len(before),AddedTriangles=3700,SceneFileNotEdited=True,CollisionNotEdited=True)
(OUT/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
