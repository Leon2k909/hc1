"""Private comparison for one T2 passive roof vent; no production writes."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,shutil,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/riverside/roof-vent-v1';ASSET=ROOT/'Assets/models/props/riverside/roof_vent_v1/review'
for p in (OUT,ASSET):p.mkdir(parents=True,exist_ok=True)
captured=[];original=P.obox
def record(m,c,right,size,paints,*a,**kw):
    if tuple(size)==(14,14,4) and paints=='rs_alu':captured.append((np.array(c),np.array(right)))
    return original(m,c,right,size,paints,*a,**kw)
P.obox=record
name,origin,yaw,L,W,tint,side,seed,extra=M.LOW_TRAILERS[0];M.build_trailer(name,L,W,tint,side,seed,extra);P.obox=original
assert captured
c,right=captured[0];old=K.Model();original(old,c,right,(14,14,4),'rs_alu');old=P.place(old,(*origin,0),yaw);M.configure(old);K.write_obj(ASSET/'old_vent.obj',old,'vent')
def faces(data):
    pts=[];mat=None
    for line in data.decode().splitlines(keepends=True):
        p=line.split();key=None
        if p and p[0]=='v':pts.append(tuple(round(float(q),4) for q in p[1:]))
        if p and p[0]=='usemtl':mat=p[1]
        if p and p[0]=='f':key=(mat,tuple(sorted(pts[int(t.split('/')[0])-1] for t in p[1:])))
        yield line,key
expected=Counter(k for _,k in faces((ASSET/'old_vent.obj').read_bytes()) if k)
path=ROOT/'Assets/models/maps/riverside/riverside_low.obj';data=path.read_bytes();kept=[];cut=[]
for line,key in faces(data):
    if key and expected[key]>0:cut.append(line);expected[key]-=1
    else:kept.append(line)
assert not sum(expected.values()) and len(cut)==12
(ASSET/'low_without_vent.obj').write_bytes(''.join(kept).encode());shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_low.mtl')
remaps=re.findall(r'\{\s*from\s*=\s*"[^\"]+"\s+to\s*=\s*"[^\"]+"\s*\}',path.with_suffix('.vmdl').read_text())
background='models/props/riverside/roof_vent_v1/review/low_without_vent.vmdl'
(ROOT/'Assets'/background).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[%R%] use_global_default=false global_default_material=""}]},{_class="RenderMeshList" children=[{_class="RenderMeshFile" name="background" filename="models/props/riverside/roof_vent_v1/review/low_without_vent.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}]}]}}
'''.replace('%R%',','.join(remaps)))
base=c-np.array((0,0,2));roof_center=P.FLOOR+P.WALL+5-abs(c[1])*5.5/(W/2+2.5)
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
plan=dict(position=K.to_world(P.local_to_world(base,(*origin,0),yaw)).tolist(),yaw=0,old_triangles=12,background=background,roof_intercept=float(roof_center-base[2]),roof_slope=float(-np.sign(c[1])*5.5/(W/2+2.5)),local_center=c.tolist(),protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(plan,indent=2));print(json.dumps(plan,indent=2))
