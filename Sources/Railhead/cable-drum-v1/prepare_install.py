"""Prepare the approved east-yard reel with distinct material aliases."""
from pathlib import Path
import hashlib,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/cable-drum-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
validation=json.loads((OUT/'validation.json').read_text())
assert validation['actual_play_mode_checked'] and validation['new_shape_unchanged'] and validation['original_wood_material_restored']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl';original=public.read_text()
assert 'cable-drum-v1/' not in original,'Already installed: inspect receipt instead'
before=OUT/'install-before';before.mkdir(exist_ok=True);(before/public.name).write_bytes(public.read_bytes())
stage=OUT/'install-stage';dest=stage/'Assets/models/maps/railhead/cable-drum-v1';dest.mkdir(parents=True,exist_ok=True)
candidate=ROOT/'Assets/models/maps/railhead/cable-drum-v1/cable_drum.obj'
obj=candidate.read_text().replace('mtllib cable_drum.mtl','mtllib installed_cable_drum.mtl')
obj=re.sub(r'(?m)^usemtl (.+)$',lambda m:'usemtl rh_cd_'+m[1],obj)
(dest/'installed_cable_drum.obj').write_text(obj)
mtl=candidate.with_suffix('.mtl').read_text();mtl=re.sub(r'(?m)^newmtl (.+)$',lambda m:'newmtl rh_cd_'+m[1],mtl)
(dest/'installed_cable_drum.mtl').write_text(mtl)
preview=(candidate.parent/'east_without_drum.vmdl').read_text();own=candidate.with_suffix('.vmdl').read_text()
pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group().replace('cable_drum.obj','installed_cable_drum.obj')
oldnode=re.search(pattern,preview,re.S).group();merged=preview.replace(oldnode,oldnode+'\n'+node,1)
remaps=re.findall(r'\{ from = "[^\n]+?\}',own)
remaps=[r.replace('from = "','from = "rh_cd_') for r in remaps]
names=lambda text:set(re.findall(r'from = "([^"]+)"',text))
assert not names('\n'.join(remaps))&names(original)
index=merged.index('\t'*7+'{ from = ');merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files=files),indent=2))
# Freeze the recovered original texture mapping in the durable generator helper.
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();A='):build.index('count=K.write_model')]
start=body.index('def original_timber_mapping():');end=body.index('timber_mapping=original_timber_mapping()')
namespace={'ROOT':ROOT,'np':np};exec(body[start:end],namespace)
coeffs=namespace['original_timber_mapping']()
frozen='timber_mapping={'+','.join(f'{k}:np.array({v.tolist()!r})' for k,v in coeffs.items())+'}'
body=body[:start]+frozen+body[end+len('timber_mapping=original_timber_mapping()'):]
helper='''"""Approved east-yard cable reel: original wood finish with the new geometry."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
MAT="materials/railhead/cable-drum-v1"
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    return m

def append_to(target):
    legacy=K.Model();D.cable_drum(legacy,1878.,-1632.,.3,'e')
    target.boxes.extend(legacy.boxes);target.hulls.extend(legacy.hulls)
    m=model()
    for paint,faces in m.polygons.items():
        alias="rh_cd_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/railhead_cable_drum.py').write_text(helper)
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import railhead_cable_drum as F
proof=OUT/'approved-generator.obj';K.write_obj(proof,F.model(),'cable_drum')
assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:]
assert not F.model().boxes and not F.model().hulls
generator=ROOT/'Tools/railhead_map.py';g=generator.read_text();(before/generator.name).write_bytes(generator.read_bytes())
old='    detail( "cable_drum", m, face + s * 18.0, -1632.0, 0.3, "e" )';assert g.count(old)==1
g=g.replace(old,'''    if s > 0:
        from railhead_cable_drum import append_to as append_approved_reel
        append_approved_reel( m )
    else:
        detail( "cable_drum", m, face + s * 18.0, -1632.0, 0.3, "e" )''')
generator.write_text(g)
script=(ROOT/'Sources/Railhead/road-barrier-v1/install.cs.txt').read_text().replace('road-barrier-v1','cable-drum-v1').replace('InstalledBarriers=1','InstalledReels=1')
(HERE/'install.cs.txt').write_text(script)
print(json.dumps(dict(reels=1,generator_matches_approved=True,material_aliases_distinct=True,staged_files=len(files))))
