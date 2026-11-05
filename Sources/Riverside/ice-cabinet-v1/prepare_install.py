"""Stage the approved cabinet into the public store ModelDoc, preserving other upgrades."""
from pathlib import Path
import hashlib,json,re
REVIEW=Path(__file__).resolve().parents[3]
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=REVIEW/'output/riverside/ice-cabinet-v1'
stage=OUT/'install-stage'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
assert sha(ROOT/m['source_model'])==m['source_sha256']
public=ROOT/m['source_vmdl'];original=public.read_text()
assert sha(public)==m['source_vmdl_sha256'] and 'ice-cabinet-v1/' not in original
before=OUT/'install-before';before.mkdir(exist_ok=True)
(before/'riverside_store.vmdl').write_bytes(public.read_bytes())
merged=original.replace(str(Path(m['source_model']).relative_to('Assets')).replace('\\','/'),'models/maps/riverside/ice-cabinet-v1/store_without_ice.obj')
assert merged!=original
meshnames=re.findall(r'_class = "RenderMeshFile"\s+name = "([^"]+)"',merged)
assert meshnames==['riverside_store','drinks_fridge'],meshnames
marker='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
idx=merged.index(marker)
end=merged.rfind('\t\t\t\t]',0,idx)
nodes=[]
materials=set()
for lod in range(3):
    obj=REVIEW/f'Assets/models/maps/riverside/ice-cabinet-v1/ice_cabinet_lod{lod}.obj'
    mtl=obj.with_suffix('.mtl')
    materials.update(re.findall(r'newmtl (\S+)',mtl.read_text()))
    target=stage/f'Assets/models/maps/riverside/ice-cabinet-v1/installed_lod{lod}.obj'
    target.parent.mkdir(parents=True,exist_ok=True)
    content=obj.read_text().replace(f'mtllib {mtl.name}',f'mtllib installed_lod{lod}.mtl')
    content=re.sub(r'(?m)^usemtl (\S+)',lambda a:'usemtl icev1_'+a[1],content)
    target.write_text(content)
    target.with_suffix('.mtl').write_text(re.sub(r'(?m)^newmtl (\S+)',lambda a:'newmtl icev1_'+a[1],mtl.read_text()))
    nodes.append('''\t\t\t\t\t{
\t\t\t\t\t\t_class = "RenderMeshFile"
\t\t\t\t\t\tname = "ice_lod%d"
\t\t\t\t\t\tfilename = "models/maps/riverside/ice-cabinet-v1/installed_lod%d.obj"
\t\t\t\t\t\timport_translation = [ 622.0, -160.0, 20.0 ]
\t\t\t\t\t\timport_scale = 1.0
\t\t\t\t\t\talign_origin_x_type = "None"
\t\t\t\t\t\talign_origin_y_type = "None"
\t\t\t\t\t\talign_origin_z_type = "None"
\t\t\t\t\t\timport_filter = { exclude_by_default = false exception_list = [] }
\t\t\t\t\t},
'''%(lod,lod))
merged=merged[:end]+''.join(nodes)+merged[end:]
groups=''.join('{ _class = "LODGroup" switch_threshold = %s meshes = [ "riverside_store", "drinks_fridge", "ice_lod%d" ] },\n'%(distance,lod) for lod,distance in enumerate((0,20,45)))
merged=merged.replace(marker,'{ _class = "LODGroupList" children = [\n'+groups+'] },\n'+marker,1)
remaps=''.join('\t'*7+'{ from = "icev1_%s.vmat" to = "materials/riverside/ice-cabinet-v1/%s.vmat" },\n'%(p,p) for p in sorted(materials))
idx=merged.index('\t'*7+'{ from = ');merged=merged[:idx]+remaps+merged[idx:]
physics='_class = "PhysicsShapeList"'
assert original[original.index(physics):]==merged[merged.index(physics):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
plan=dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()},physics_unchanged=True)
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(dict(staged_files=len(plan['files']),lods=3,triangles=m['triangles'],physics_unchanged=True,preserved_meshes=meshnames),indent=2))
