"""Freeze the approved pallet and stage a narrow, guarded public installation."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/brick-pallet-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
validation=json.loads((OUT/'validation.json').read_text());assert validation['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl';source=ROOT/manifest['source'];original=public.read_text()
assert 'installed_brick_pallet.obj' not in original,'Already installed; inspect receipt'
before=OUT/'install-before';stage=OUT/'install-stage';dest=stage/'Assets/models/maps/railhead/brick-pallet-v1';dest.mkdir(parents=True,exist_ok=True)
for path in (public,source,ROOT/'Tools/railhead_map.py'):
 backup=before/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
candidate=ROOT/'Assets/models/maps/railhead/brick-pallet-v1/brick_pallet.obj'
obj=candidate.read_text().replace('mtllib brick_pallet.mtl','mtllib installed_brick_pallet.mtl')
obj=re.sub(r'(?m)^usemtl (.+)$',lambda m:'usemtl rh_bp_'+m[1],obj);(dest/'installed_brick_pallet.obj').write_text(obj)
mtl=re.sub(r'(?m)^newmtl (.+)$',lambda m:'newmtl rh_bp_'+m[1],candidate.with_suffix('.mtl').read_text());(dest/'installed_brick_pallet.mtl').write_text(mtl)
# Retain the live base's filename/material library; remove only the preview's matched faces.
base=(candidate.parent/'east_without_pallet.obj').read_text().replace('mtllib east_without_pallet.mtl','mtllib '+source.with_suffix('.mtl').name)
target=stage/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(base)
own=candidate.with_suffix('.vmdl').read_text();pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group().replace('brick_pallet.obj','installed_brick_pallet.obj')
oldnode=re.search(pattern,original,re.S).group();merged=original.replace(oldnode,oldnode+'\n'+node,1)
remaps=[r.replace('from = "','from = "rh_bp_') for r in re.findall(r'\{ from = "[^\n]+?\}',own)]
assert not set(re.findall(r'from = "([^"]+)"','\n'.join(remaps)))&set(re.findall(r'from = "([^"]+)"',original))
index=merged.index('\t'*7+'{ from = ');merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
plan=dict(before={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (public,source)},files=files,new_triangles=manifest['triangles'],old_triangles=manifest['original_triangles'])
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();frame='):build.index('legacy=K.Model();')]
body=body[:body.index(';count=K.write_model')]
helper='''"""Approved east Railhead brick pallet, preserving its original collider."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
import belltower_furniture as F
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    return m

def append_to(target):
    legacy=K.Model();D.brick_pallet(legacy,1884.,-1580.,.3,'n')
    target.boxes.extend(legacy.boxes);target.hulls.extend(legacy.hulls)
    m=model()
    for paint,faces in m.polygons.items():
        alias='rh_bp_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/railhead_brick_pallet.py').write_text(helper)
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import railhead_brick_pallet as F
proof=OUT/'approved-generator.obj';K.write_obj(proof,F.model(),'brick_pallet')
assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:]
assert not F.model().boxes and not F.model().hulls
generator=ROOT/'Tools/railhead_map.py';g=generator.read_text();old='    detail( "brick_pallet", m, face + s * 24.0, -1580.0, 0.3, "n" )';assert g.count(old)==1
g=g.replace(old,'''    if s > 0:
        from railhead_brick_pallet import append_to as append_approved_brick_pallet
        append_approved_brick_pallet( m )
    else:
        detail( "brick_pallet", m, face + s * 24.0, -1580.0, 0.3, "n" )''');generator.write_text(g)
script=(ROOT/'Sources/Railhead/cable-drum-v1/install.cs.txt').read_text().replace('cable-drum-v1','brick-pallet-v1').replace('InstalledReels','InstalledPallets');(HERE/'install.cs.txt').write_text(script)
print(json.dumps(dict(pallets=1,staged_files=len(files),new_triangles=manifest['triangles'],old_triangles=manifest['original_triangles'],generator_matches_approved=True)))
