from pathlib import Path
from collections import Counter
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/stair-treads-v1';ASSETS=ROOT/'Assets/models/maps/sewage'
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
plan=json.loads((OUT/'plan.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for filename,wanted in plan['install_files'].items():assert sha(ASSETS/filename)==wanted,filename
assert sha(ASSETS/'sewage_catwalks_hulls_metal.obj')==plan['hull_hash']
_,old=S.read_obj(OUT/'baseline/sewage_catwalks.obj')
_,removed=S.read_obj(OUT/'old-treads.obj')
_,added=S.read_obj(OUT/'new-treads.obj')
_,current=S.read_obj(ASSETS/'sewage_catwalks.obj')
assert Counter(current)==Counter(old)-Counter(removed)+Counter(added)
report=dict(InstalledFilesMatchStage=True,CollisionHullUnchanged=True,
    RetainedTriangles=plan['retained_triangles'],RemovedTriangles=len(removed),AddedTriangles=len(added),
    OtherCatwalkFacesUnchanged=True,ApprovedWarningTexturePresent=(ROOT/'Assets/materials/sewage/warning-sign-v1/warning_color_v2.png').exists(),
    OldWarningTextureRemoved=not (ROOT/'Assets/materials/sewage/warning_color.png').exists())
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
capture=(HERE/'capture.cs.txt').read_text()
original='signage.Model=Model.Load("models/maps/sewage/stair-treads-v1/"+variant+".vmdl");'
replacement='signage.Model=Model.Load(variant=="after"?"models/maps/sewage/sewage_catwalks.vmdl":"models/maps/sewage/stair-treads-v1/before.vmdl");'
assert original in capture
capture=capture.replace(original,replacement)
capture=capture.replace('foreach(var view in views)foreach(var variant','foreach(var view in views.Where(v=>v.Name=="flight"))foreach(var variant')
(HERE/'capture-installed.cs.txt').write_text(capture)
print(json.dumps(report,indent=2))
