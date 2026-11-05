"""A real aluminium slider frame for the selected flat T2 window; review only."""
from pathlib import Path
from collections import Counter
import json,sys,math,hashlib
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/sliding-window-v1';STAGE=OUT/'stage/Assets';RES='models/props/riverside/sliding_window_v1';MODEL=STAGE/RES;MODEL.mkdir(parents=True,exist_ok=True)
target=json.loads((OUT/'target.json').read_text());W,H=target['width'],target['height'];X,Y,Z=np.eye(3)
def model(lod):
    m=K.Model();corners=(6,4,2)[lod]
    def box(c,size,paint='rs_alu',b=.06):
        if lod<2 and b:G.bevel_box(m,np.array(c,float),(X,Y,Z),size,paint,bevel=b)
        else:m.oriented_box(np.array(c,float),(X,Y,Z),size,paint)
    def outline(w,h,r):
        return [np.array((cx+r*math.cos(a),0,cz+r*math.sin(a))) for cx,cz,angle in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)] for a in np.linspace(math.radians(angle),math.radians(angle+90),corners+1)]
    def ring(cx,cz,w,h,border,r,depth,thick,paint='rs_alu'):
        outer=outline(w,h,r);inner=outline(w-border*2,h-border*2,max(.08,r-border))
        c=np.array((cx,-depth,cz));back=np.array((0,thick,0));out=-Y
        for k in range(len(outer)):
            j=(k+1)%len(outer);a,b,i,jj=outer[k]+c,outer[j]+c,inner[k]+c,inner[j]+c
            G._face(m,paint,[a,b,jj,i],towards=out)
            G._face(m,paint,[a+back,i+back,jj+back,b+back],towards=-out)
            G._face(m,paint,[a,a+back,b+back,b],towards=outer[k])
            G._face(m,paint,[i,jj,jj+back,i+back],towards=-inner[k])
    # Mounting flange and raised rounded extrusion surround an actual open aperture.
    ring(0,0,W+3,H+3,1.3,2.0,.32,.25)
    ring(0,0,W+.4,H+.4,.38,.85,.64,.28,'rs_rubber')
    ring(0,0,W+1.7,H+1.7,.74,1.35,1.45,.95)
    # Two separate sashes occupy offset tracks, with rubber glazing beads.
    for side,depth in ((-1,1.35),(1,.94)):
        cx=side*(W/4-.1)
        ring(cx,0,W/2+.2,H+.15,.68,.65,depth,.32)
        ring(cx,0,W/2-1.05,H-1.05,.13,.23,depth+.035,.10,'rs_rubber')
    # Meeting stile, wool-pile seal and operating latch; no new pane replaces the existing artwork.
    box((-.08,-1.63,0),(.62,.42,H-.25),b=.10)
    box((.38,-1.42,0),(.14,.16,H-.7),'rs_rubber',.025)
    box((.8,-1.75,-4.6),(1.3,.36,3.5),'rs_rubber',.18)
    box((.8,-1.98,-4.6),(.86,.3,2.8),b=.16)
    box((1.35,-2.10,-4.1),(1.15,.22,.55),b=.10)
    # Deep lower runner has an open water channel and real weep slots between the lips.
    box((0,-1.14,-H/2-.7),(W+2.7,1.95,.45),b=.10)
    for depth in (.35,1.1,1.92):box((0,-depth,-H/2-.30),(W+2.1,.16,.65),b=.04)
    for x in (-W*.32,W*.32):
        box((x,-2.04,-H/2-.52),(1.35,.05,.22),'rs_rubber',.05)
        box((x,-2.10,-H/2-.27),(1.7,.20,.16),b=.05)
    # Formed drip sill and folded end caps retain the original sill's full width.
    G._face(m,'rs_alu',[(-W/2-2.5,-.1,-H/2-1.8),(W/2+2.5,-.1,-H/2-1.8),(W/2+2.5,-2.7,-H/2-2.6),(-W/2-2.5,-2.7,-H/2-2.6)],towards=Z)
    box((0,-2.63,-H/2-2.8),(W+5,.22,.60),b=.07)
    for x in (-W/2-2.3,W/2+2.3):box((x,-1.4,-H/2-2.20),(.28,2.6,.55),b=.05)
    if lod<2:
        for x in (-W/2-.92,W/2+.92):
            for z in (-H/2+.8,0,H/2-.8):
                G.lathe_axis(m,(x,-.36,z),-Y,[(0,0),(.19,0),(.19,.10),(0,.10)],'rs_alu',sides=10 if lod==0 else 6)
                if lod==0:box((x,-.475,z),(.23,.025,.04),'rs_rubber',0)
    R.configure(m);return m
counts=[];models=[]
for lod in range(3):
    m=model(lod);models.append(m);counts.append(K.write_obj(MODEL/f'window_lod{lod}.obj',m,f'window_lod{lod}'))
K.write_vmdl(MODEL/'window.vmdl',RES,'window_lod0',models[0]);doc=(MODEL/'window.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/window_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3));groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,25,70)))
(MODEL/'window.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {meshes} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
old=K.Model();P.window(old,target['world_plan'],target['right'],W,H,target['style'],target['seed']);old.polygons={k:v for k,v in old.polygons.items() if k=='rs_alu'};R.configure(old);K.write_obj(OUT/'old.obj',old,'old')
def records(path):
    lines=path.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):faces.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,faces
_,wanted=records(OUT/'old.obj');remaining=Counter(key for _,key in wanted);src=ROOT/'Assets/models/maps/riverside/riverside_low.obj';lines,current=records(src);cut=set()
for i,key in current:
    if remaining[key]:remaining[key]-=1;cut.add(i)
assert len(cut)==14 and not +remaining,'Selected frame differs from current saved trailer'
(MODEL/'preview.obj').write_text(''.join(line for i,line in enumerate(lines) if i not in cut));(MODEL/'riverside_low.mtl').write_bytes(src.with_suffix('.mtl').read_bytes())
(MODEL/'preview.vmdl').write_text(src.with_suffix('.vmdl').read_text().replace('filename = "models/maps/riverside/riverside_low.obj"',f'filename = "{RES}/preview.obj"'))
for name in ('old.obj','old.mtl'):(OUT/name).unlink()
protected=[src,src.with_suffix('.vmdl'),src.with_suffix('.mtl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
manifest=dict(preview_only=True,triangles=counts,old_faces=14,cut=sorted(cut),position_world=K.to_world(target['world_plan']).tolist(),existing_upgrade_audit=target['existing_upgrade_audit'],
 protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'triangles':counts,'old_faces':14,'position':manifest['position_world']}))
