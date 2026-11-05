from pathlib import Path
import sys,json,hashlib,re,collections,ast
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'));sys.path.insert(0,str(Path(__file__).absolute().parent))
import map_kit as K,riverdale_parts as G,riverside_parts as P,riverside_map as R
from geometry import make
OUT=ROOT/'output/riverside/yard-fence-v1';STAGE=OUT/'stage';RES='models/props/riverside/yard_fence_v1';MODEL=STAGE/'Assets'/RES;MODEL.mkdir(parents=True,exist_ok=True)
origin=np.array((-1400.,960.,0.))
counts=[K.write_obj(MODEL/f'fence_lod{i}.obj',make(i),f'fence_lod{i}') for i in range(3)]
K.write_vmdl(MODEL/'fence.vmdl',RES,'fence_lod0',make(0));t=(MODEL/'fence.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files=''.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/fence_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,20,45)))
(MODEL/'fence.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{files}]}},\n{{_class="LODGroupList" children=[{groups}]}},'+t[b:])
old=K.Model();P.plank_fence(old,[(-1400,960),(-1400,1460)],seed=1);R.configure(old);K.write_obj(OUT/'legacy_absolute.obj',old,'old_fence')
local=K.Model();P.plank_fence(local,[(0,0),(500,0)],seed=1);local.boxes.clear();local.hulls.clear();R.configure(local);K.write_model(MODEL,RES,'legacy_fence',local)
tree=ast.parse((ROOT/'Sources/Riverside/still-here-board-v1/prepare_install.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='records');env={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'records','exec'),env);records=env['records']
_,fs=records(OUT/'legacy_absolute.obj');want=collections.Counter(k for _,k in fs);vmdl=ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl';vt=vmdl.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
 p=ROOT/'Assets'/ref
 if not p.exists():continue
 ls,fs=records(p)
 if not want-collections.Counter(k for _,k in fs):source=p;break
assert source,'Original entrance steps do not match saved store input'
cut=set()
for i,k in fs:
 if want[k]:cut.add(i);want[k]-=1
assert len(cut)>500 and not +want
(MODEL/'dressing_without_fence.obj').write_text(''.join(l for i,l in enumerate(ls) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib dressing_without_fence.mtl'));(MODEL/'dressing_without_fence.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'dressing_without_fence.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/dressing_without_fence.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene'];external={('Assets/'+v):sha(ROOT/'Assets'/v) for v in make(0).material_overrides.values()}
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),yaw=90,removed_old_triangles=len(cut),resource=RES+'/fence.vmdl',background=RES+'/dressing_without_fence.vmdl',protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},external_files=external,files={p.relative_to(STAGE).as_posix():sha(p) for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
