from pathlib import Path
import sys,json,hashlib,collections,re,ast
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;sys.path.insert(0,str(ROOT/'Tools'));sys.path.insert(0,str(HERE))
import map_kit as K,riverdale_map as R,riverdale_yard as Y
from geometry import make
OUT=ROOT/'output/riverdale/hydrant-v1';STAGE=OUT/'stage';RES='models/props/riverdale/hydrant_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
MATERIAL=STAGE/'Assets/materials/riverdale/hydrant_v1'
from surfaces import build as build_surfaces
build_surfaces(MATERIAL)
# Retain the previously reviewed candidate for a direct v1/v2 comparison, without altering the saved map.
if not (MODEL/'previous.vmdl').exists():
 source=ROOT/'Assets'/RES
 for i in range(3):
  (MODEL/f'previous_lod{i}.obj').write_text((source/f'hydrant_lod{i}.obj').read_text().replace(f'mtllib hydrant_lod{i}.mtl',f'mtllib previous_lod{i}.mtl'))
  (MODEL/f'previous_lod{i}.mtl').write_bytes((source/f'hydrant_lod{i}.mtl').read_bytes())
 (MODEL/'previous.vmdl').write_text((source/'hydrant.vmdl').read_text().replace('/hydrant_lod','/previous_lod'))
counts=[K.write_obj(MODEL/f'hydrant_lod{i}.obj',make(i),f'hydrant_lod{i}') for i in range(3)]
K.write_vmdl(MODEL/'hydrant.vmdl',RES,'hydrant_lod0',make(0));t=(MODEL/'hydrant.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=''.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/hydrant_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,20,45)))
(MODEL/'hydrant.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{files}]}},\n{{_class="LODGroupList" children=[{groups}]}},'+t[b:])
old=K.Model();Y.hydrant(old,'lane hydrant west',(-380,2436),(0,-1));R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_hydrant')
local=K.Model();Y.hydrant(local,'legacy',(0,0),(0,-1));R.configure(local);K.write_model(MODEL,RES,'legacy_hydrant',local)
tree=ast.parse((ROOT/'Sources/Riverside/still-here-board-v1/prepare_install.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='records');env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'records','exec'),env);records=env['records']
_,fs=records(OUT/'legacy_absolute.obj');want=collections.Counter(k for _,k in fs);vmdl=ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.vmdl';vt=vmdl.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
 p=ROOT/'Assets'/ref
 if not p.exists():continue
 ls,fs=records(p)
 if not want-collections.Counter(k for _,k in fs):source=p;break
assert source,'Original north-lane hydrant no longer matches saved yard mesh'
cut=set()
for i,k in fs:
 if want[k]:cut.add(i);want[k]-=1
assert len(cut)>200 and not +want
(MODEL/'yard_without_hydrant.obj').write_text(''.join(l for i,l in enumerate(ls) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib yard_without_hydrant.mtl'));(MODEL/'yard_without_hydrant.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'yard_without_hydrant.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/yard_without_hydrant.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene'];external={('Assets/'+v):sha(ROOT/'Assets'/v) for v in ('materials/riverdale/rv_yd_red.vmat','materials/riverdale/rv_dark.vmat','materials/riverdale/rv_zinc.vmat')}
m=dict(preview_only=True,revision=2,triangles=counts,position=[2436,380,0],yaw=0,removed_old_triangles=len(cut),resource=RES+'/hydrant.vmdl',background=RES+'/yard_without_hydrant.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()});(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
