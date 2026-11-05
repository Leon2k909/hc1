from pathlib import Path
from collections import Counter
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/sewage/salvage-drums-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,sewage_map as R,riverdale_splice as S
import drums
R.PAINTS.update(steel=96,rust=96)
assert not (ROOT/'Tools/sewage_salvage_drums.py').exists(),'Already installed; historical review must be retained'
source=ROOT/'Assets/models/maps/boxyard/oil_drum_v2/oil_drum_lod0.obj';snapshot=HERE/'source-drum-lod0.obj'
if snapshot.exists():assert snapshot.read_bytes()==source.read_bytes(),'Source mesh changed'
else:shutil.copy2(source,snapshot)
folder=STAGE/'Assets/materials/sewage/salvage-drums-v1';assert (folder/'salvage_drum_normal.png').exists(),'Run paint_drum.py first'
for name in ('olive','oxide'):
 text=(ROOT/'Assets/models/maps/boxyard/oil_drum_v2/oil_drum_blue.vmat').read_text().replace('models/maps/boxyard/oil_drum_v2/','materials/sewage/salvage-drums-v1/').replace('oil_drum_blue_color.png','salvage_drum_'+name+'_color.png').replace('oil_drum_','salvage_drum_')
 (folder/(name+'.vmat')).write_text(text)
modeldir=STAGE/'Assets/models/maps/sewage/salvage-drums-v1';modeldir.mkdir(parents=True,exist_ok=True)
old=drums.original(R.model(),*drums.PLACEMENTS[0]);K.write_obj(OUT/'sample-original.obj',old,'sewage_details')
_,faces=S.read_obj(OUT/'sample-original.obj');_,published=S.read_obj(ROOT/'Assets/models/maps/sewage/sewage_details.obj')
assert not Counter(faces)-Counter(published),'Original drum differs'
from riverside_parts import place
preview=place(old,-__import__('numpy').array(drums.PLACEMENTS[0]),0);preview.boxes=[];preview.hulls=[]
K.write_obj(modeldir/'before.obj',preview,'sewage_details');K.write_vmdl(modeldir/'before.vmdl','models/maps/sewage/salvage-drums-v1','before',preview)
translated=[];e,n,z=drums.PLACEMENTS[0]
for mat,corners in faces:
 q=[]
 for p,uv,nrm in corners:
  a,b,c=map(float,p.split());q.append((f'{a+e:.3f} {b-z:.3f} {c-n:.3f}',uv,nrm))
 translated.append((mat,tuple(q)))
S.write_obj(modeldir/'before.obj',['mtllib before.mtl\n','o before\n'],translated)
counts={}
for name in ('olive','oxide'):
 new=drums.drum(K.Model(),(0,0,0),name,15)
 counts[name]=K.write_obj(modeldir/(name+'.obj'),new,'sewage_details');K.write_vmdl(modeldir/(name+'.vmdl'),'models/maps/sewage/salvage-drums-v1',name,new)
plan=dict(triangles=counts,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()},source_hash=hashlib.sha256(snapshot.read_bytes()).hexdigest())
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print(counts)
for name in ('native.py','import_preview.cs.txt','compile.py','capture.cs.txt'):
 text=(ROOT/'Sources/Sewage/crane-blocks-v1'/name).read_text().replace('crane-blocks-v1','salvage-drums-v1')
 if name=='compile.py':text=text.replace("('before','crane')","('before','olive','oxide')")
 if name=='capture.cs.txt':
  text=text.replace('"before","crane"','"before","olive"').replace('Crane lower block comparison','Salvage drum comparison')
  text=text.replace('new Vector3(0,0,-56)','new Vector3(0,0,0)').replace('W(105,-210,80)','W(125,0,75)').replace('W(0,0,20)','W(0,0,27)').replace('FieldOfView=39','FieldOfView=31')
 (HERE/name).write_text(text)
