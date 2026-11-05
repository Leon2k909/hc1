from pathlib import Path
import json,hashlib,sys,re,importlib.util
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/shelving-v1';stage=OUT/'install-stage'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());assert json.loads((OUT/'verification.json').read_text())['actual_play_verified']
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
public=ROOT/m['source_vmdl'];original=public.read_text();assert sha(public)==m['source_vmdl_sha256'] and sha(ROOT/m['source_model'])==m['source_sha256']
assert 'shv1_' not in original
before=OUT/'install-before';before.mkdir(exist_ok=True);(before/'riverside_store.vmdl').write_bytes(public.read_bytes())
s=(HERE/'build.py').read_text(encoding='utf-8');body=s[s.index('X=np.array'):s.index('\ntriangles=[]')]
head='''import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/shelving-v1"
'''
(HERE/'geometry.py').write_text(head+body,encoding='utf-8')
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import riverside_parts as P
spec=importlib.util.spec_from_file_location('approved_geometry',HERE/'geometry.py');geo=importlib.util.module_from_spec(spec);spec.loader.exec_module(geo)
for lod in range(3):
    combined=K.Model()
    for n,negative_e,z in m['positions']:
        moved=P.place(geo.model(lod),(-negative_e,n,z),90)
        for paint,faces in moved.polygons.items():
            alias='shv1_'+paint;combined.material_overrides[alias]=moved.material_overrides[paint];combined.tile_overrides[alias]=moved.tile_overrides[paint]
            for i,(pts,normal) in enumerate(faces):combined.polygon(alias,pts,normal,uv=moved.polygon_uvs.get((paint,i)),normals=moved.polygon_normals.get((paint,i)))
    target=stage/f'Assets/models/maps/riverside/shelving-v1/installed_lod{lod}.obj';target.parent.mkdir(parents=True,exist_ok=True)
    count=K.write_obj(target,combined,f'installed_lod{lod}');assert count==m['triangles'][lod]*4
source_resource=str(Path(m['source_model']).relative_to('Assets')).replace('\\','/')
merged=original.replace(source_resource,'models/maps/riverside/shelving-v1/store_without_shelving.obj')
def span(text,kind):
    at=text.index('_class = "'+kind+'"');start=text.rfind('{',0,at);depth=0;quoted=False
    for end in range(start,len(text)):
        c=text[end]
        if c=='"':quoted=not quoted
        if quoted:continue
        if c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth==0:return start,end+1
    raise ValueError('Unclosed '+kind)
nodes='\n'.join('{_class = "RenderMeshFile" name = "shelving_lod%d" filename = "models/maps/riverside/shelving-v1/installed_lod%d.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {exclude_by_default = false exception_list = []}},'%(lod,lod) for lod in range(3))
start,end=span(merged,'RenderMeshList');block=merged[start:end];at=block.rfind(']');merged=merged[:start]+block[:at]+nodes+block[at:]+merged[end:]
start,end=span(merged,'LODGroupList');groups=[]
for distance,names in re.findall(r'_class = "LODGroup"\s+switch_threshold = ([\d.]+)\s+meshes = \[([^\]]+)\]',merged[start:end]):
    d=float(distance);lod=2 if d>=25 else 1 if d>=10 else 0
    groups.append('{_class = "LODGroup" switch_threshold = %g meshes = [%s]},'%(d,names+f',"shelving_lod{lod}"'))
assert len(groups)==7
merged=merged[:start]+'{_class = "LODGroupList" children = [\n'+'\n'.join(groups)+'\n]}'+merged[end:]
remaps=''.join('\t'*7+'{ from = "shv1_%s.vmat" to = "materials/riverside/shelving-v1/%s.vmat" },\n'%(p,p) for p in sorted(geo.model(0).polygons))
at=merged.index('\t'*7+'{ from = ');merged=merged[:at]+remaps+merged[at:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged,encoding='utf-8')
plan=dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()},units=4,physics_unchanged=True)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
source=(ROOT/'Sources/Riverside/counter-v1/install.cs.txt').read_text(encoding='utf-8').replace('counter-review','shelving-review').replace('counter-v1','shelving-v1').replace('Counters=1','ShelvingUnits=4')
(HERE/'install.cs.txt').write_text(source,encoding='utf-8')
print(json.dumps(dict(files=len(plan['files']),units=4,triangles=[n*4 for n in m['triangles']],physics_unchanged=True),indent=2))
