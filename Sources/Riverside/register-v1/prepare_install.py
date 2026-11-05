"""Merge only the approved register into the current public store ModelDoc."""
from pathlib import Path
import json,re,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
REVIEW=Path(__file__).resolve().parents[3]
OUT=REVIEW/'output/riverside/register-v1';stage=OUT/'install-stage'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text())
assert json.loads((OUT/'verification.json').read_text())['actual_play_verified']
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
public=ROOT/m['source_vmdl'];original=public.read_text()
assert sha(public)==m['source_vmdl_sha256'] and sha(ROOT/m['source_model'])==m['source_sha256']
assert 'regv1_' not in original,'Already installed: inspect receipt'
before=OUT/'install-before';before.mkdir(exist_ok=True);(before/'riverside_store.vmdl').write_bytes(public.read_bytes())
source_resource=str(Path(m['source_model']).relative_to('Assets')).replace('\\','/')
merged=original.replace(source_resource,'models/maps/riverside/register-v1/store_without_register.obj')
def span(text,kind):
    at=text.index('_class = "'+kind+'"');start=text.rfind('{',0,at);depth=0;quote=False;escape=False
    for end in range(start,len(text)):
        c=text[end]
        if quote:
            if escape:escape=False
            elif c=='\\':escape=True
            elif c=='"':quote=False
        elif c=='"':quote=True
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth==0:return start,end+1
    raise ValueError('Unclosed '+kind)
nodes=[];materials=set()
for lod in range(3):
    source=REVIEW/f'Assets/models/maps/riverside/register-v1/register_lod{lod}.obj'
    mtl=source.with_suffix('.mtl');materials.update(re.findall(r'newmtl (\S+)',mtl.read_text()))
    target=stage/f'Assets/models/maps/riverside/register-v1/installed_lod{lod}.obj';target.parent.mkdir(parents=True,exist_ok=True)
    content=source.read_text().replace(f'mtllib {mtl.name}',f'mtllib installed_lod{lod}.mtl')
    target.write_text(re.sub(r'(?m)^usemtl (\S+)',lambda a:'usemtl regv1_'+a[1],content))
    target.with_suffix('.mtl').write_text(re.sub(r'(?m)^newmtl (\S+)',lambda a:'newmtl regv1_'+a[1],mtl.read_text()))
    nodes.append('''{ _class = "RenderMeshFile" name = "register_lod%d" filename = "models/maps/riverside/register-v1/installed_lod%d.obj" import_translation = [935.0,-120.0,60.0] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {exclude_by_default = false exception_list = []} },
'''%(lod,lod))
start,end=span(merged,'RenderMeshList');block=merged[start:end];at=block.rfind(']');block=block[:at]+''.join(nodes)+block[at:];merged=merged[:start]+block+merged[end:]
start,end=span(merged,'LODGroupList');oldgroups=[]
for distance,names in re.findall(r'_class = "LODGroup"\s+switch_threshold = ([\d.]+)\s+meshes = \[([^\]]+)\]',merged[start:end]):oldgroups.append((float(distance),re.findall(r'"([^"]+)"',names)))
assert len(oldgroups)==3
groups=[]
for distance in sorted(set([d for d,_ in oldgroups]+[0,10,25])):
    names=max((g for g in oldgroups if g[0]<=distance),key=lambda g:g[0])[1]
    lod=2 if distance>=25 else 1 if distance>=10 else 0
    groups.append('{_class = "LODGroup" switch_threshold = %g meshes = [%s]},'%(distance,','.join('"'+name+'"' for name in names+[f'register_lod{lod}'])))
merged=merged[:start]+'{_class = "LODGroupList" children = [\n'+'\n'.join(groups)+'\n]}'+merged[end:]
remaps=''.join('\t'*7+'{ from = "regv1_%s.vmat" to = "materials/riverside/register-v1/%s.vmat" },\n'%(p,p) for p in sorted(materials))
at=merged.index('\t'*7+'{ from = ');merged=merged[:at]+remaps+merged[at:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
plan=dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()},thresholds=[0,10,20,25,45],physics_unchanged=True)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
script=(ROOT/'Sources/Riverside/ice-cabinet-v1/install.cs.txt').read_text().replace('C:/sbox-projects/hc1/ice-cabinet-review','C:/sbox-projects/hc1/register-review').replace('ice-cabinet-v1','register-v1').replace('Cabinets=1','Registers=1')
(Path(__file__).parent/'install.cs.txt').write_text(script)
print(json.dumps(dict(staged_files=len(plan['files']),lod_groups=len(groups),physics_unchanged=True),indent=2))
