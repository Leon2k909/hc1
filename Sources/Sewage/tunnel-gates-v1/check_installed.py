from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/tunnel-gates-v1';ASSETS=ROOT/'Assets/models/maps/sewage'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
plan=json.loads((OUT/'plan.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for filename,wanted in plan['install_files'].items():assert sha(ASSETS/filename)==wanted,filename
assert sha(ASSETS/'sewage_shell_hulls_default.obj')==plan['hull_hash']
_,old=S.read_obj(OUT/'baseline/sewage_shell.obj')
_,removed=S.read_obj(OUT/'old-ends.obj')
_,added=S.read_obj(OUT/'new-gates.obj')
_,current=S.read_obj(ASSETS/'sewage_shell.obj')
assert Counter(current)==Counter(old)-Counter(removed)+Counter(added)
assert all((ASSETS/f'stair-treads-v1/{v}.vmdl').exists() for v in ('before','after'))
report=dict(InstalledFilesMatchStage=True,Gates=2,CollisionHullUnchanged=True,
 RetainedTriangles=plan['retained_triangles'],RemovedTriangles=len(removed),AddedTriangles=len(added),
 AllUnrelatedShellFacesUnchanged=True,BothStairVersionsKept=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
capture=(HERE/'capture.cs.txt').read_text()
original='signage.Model=Model.Load("models/maps/sewage/tunnel-gates-v1/"+variant+".vmdl");'
replacement='signage.Model=Model.Load(variant=="after"?"models/maps/sewage/sewage_shell.vmdl":"models/maps/sewage/tunnel-gates-v1/before.vmdl");'
assert original in capture
(HERE/'capture-installed.cs.txt').write_text(capture.replace(original,replacement))
print(json.dumps(report,indent=2))
