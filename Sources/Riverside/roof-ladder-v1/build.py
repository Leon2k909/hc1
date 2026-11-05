from pathlib import Path
import sys,inspect,math,json,hashlib,collections,re
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
import lowtide_quay_ladders as A
RES='models/maps/riverside/roof-ladder-v1';MODEL=REVIEW/'Assets'/RES;OUT=REVIEW/'output/riverside/roof-ladder-v1'
MODEL.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
H=R.RAISED+P.FLOOR+P.WALL+6
def model(lod):
    s=inspect.getsource(A.model)
    edits={'def model(n=-1450.):':'def model(n=0.):','for n in (-8,8):':'for n in (-9,9):','P(234,n,-132),P(234,n,15)':f'P(234,n,0),P(234,n,{H+18})','np.linspace(math.pi,0,17)':f'np.linspace(math.pi,0,{(17,11,7)[lod]})','15+3*math.sin(angle)':f'{H+18}+3*math.sin(angle)','P(240,n,1.0)':'P(240,n,roof(n)+1.0)','box(240,n,.6':'box(240,n,roof(n)+.6','P(240,n+offset,1.21),P(240,n+offset,1.5)':'P(240,n+offset,roof(n+offset)+1.21),P(240,n+offset,roof(n+offset)+1.5)','for z in (-15,-66,-116):':'for z in (150.,200.):','box(239.65,n,z':'box(274-38*z/220,n,z','P(239.3,n,z)':'P(273.65-38*z/220,n,z)','bolt(239.2,n,z+dz)':'bolt(273.55-38*z/220,n,z+dz)','P(234,n,-132),P(234,n,-130.7)':'P(234,n,0),P(234,n,1.3)','range(-120,0,12)':f'range(12,{int(H)},12)','P(234,-8,z),P(234,8,z)':'P(234,-9,z),P(234,9,z)','2.9,14.1,.32':'2.9,16.1,.32','.17,13.9,.22':'.17,15.9,.22','np.linspace(-6,6,9)':f'np.linspace(-7,7,{(9,5,0)[lod]})','(-7.4,7.4)':'(-8.4,8.4)','points=[np.asarray(p,float) for p in points];rings=[];norms=[]':f'sides=max(4,int(round(sides*{(1,.67,.42)[lod]})));points=[np.asarray(p,float) for p in points];rings=[];norms=[]'}
    for a,b in edits.items():assert s.count(a)==1,a;s=s.replace(a,b)
    env=dict(A.__dict__);env['roof']=lambda n:H-1-5.5*abs(40+n)/62.5;exec(compile(s,'fitted-approved-roof-ladder','exec'),env);proto=env['model']()
    matrix=np.array(((1,0,38/H),(0,1,0),(0,0,1.)),float);normal_matrix=np.linalg.inv(matrix).T;m=K.Model()
    for paint,polys in proto.polygons.items():
        for i,(pts,normal) in enumerate(polys):
            points=[matrix@(q-np.array((234.,0.,0.))) for q in pts];ns=proto.polygon_normals.get((paint,i))
            G.card(m,paint,points,normal_matrix@normal,uv=proto.polygon_uvs.get((paint,i)),normals=None if ns is None else [K.normalise(normal_matrix@n) for n in ns])
    m.material_overrides=dict(proto.material_overrides);m.material_overrides['paint']='materials/riverside/tower_ladder_legacy_steel/steel.vmat';m.tile_overrides=dict(proto.tile_overrides)
    return m
models=[model(i) for i in range(3)];counts=[K.write_obj(MODEL/f'ladder_lod{i}.obj',models[i],f'ladder_lod{i}') for i in range(3)];K.write_vmdl(MODEL/'ladder.vmdl',RES,'ladder_lod0',models[0])
t=(MODEL/'ladder.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
nodes='\n'.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/ladder_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups='\n'.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,20,45)))
(MODEL/'ladder.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{nodes}]}},\n{{_class="LODGroupList" children=[{groups}]}},'+t[b:],encoding='utf-8')
old=K.Model();foot=np.array((-340.,40.,0));top=np.array((-302.,40.,H))
for dy in (-9,9):P.rod(old,foot+[0,dy,0],top+[0,dy,0],.8,'rs_alu',6)
for k in range(1,int(H/12)+1):
    q=foot+(top-foot)*k/(int(H/12)+1);P.rod(old,q+[0,-9,0],q+[0,9,0],.55,'rs_alu',5)
R.configure(old);local=P.place(old,-foot,0);K.write_model(MODEL,RES,'legacy_ladder',local)
absolute=P.place(old,(737,747,96),90);oldcount=K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_ladder')
def records(path):
    lines=path.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):faces.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,faces
_,keys=records(OUT/'legacy-absolute.obj');want=collections.Counter(k for _,k in keys);public=ROOT/'Assets/models/maps/riverside/riverside_levee.vmdl';text=public.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text):
    f=ROOT/'Assets'/ref;lines,faces=records(f)
    if not want-collections.Counter(k for _,k in faces):source=f;break
assert source,'Saved roof ladder differs; inspect before changing it'
removed=set()
for i,k in faces:
    if want[k]:removed.add(i);want[k]-=1
assert not +want
(MODEL/'levee_without_ladder.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib levee_without_ladder.mtl'))
(MODEL/'levee_without_ladder.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'levee_without_ladder.vmdl').write_text(text.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/levee_without_ladder.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=dict(preview_only=True,triangles=counts,original_triangles=oldcount,position=[407,-697,96],yaw=90,height=H,source_model=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),source_vmdl=public.relative_to(ROOT).as_posix(),source_vmdl_sha256=sha(public),external_files={p:sha(ROOT/'Assets'/p) for p in set(models[0].material_overrides.values())},files={p.relative_to(REVIEW).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k not in ('files','external_files')},indent=2))
