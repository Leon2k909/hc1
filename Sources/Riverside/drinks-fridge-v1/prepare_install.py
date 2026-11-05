"""Prepare only the approved porch fridge; never regenerate the shared map."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverside/drinks-fridge-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'validation.json').read_text())['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text())
changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
# Reviewed concurrent supply-crate/fire edits and editor scene serialization.
# Retain the original preview guard and record a fresh integration baseline.
assert set(changed)<= {'Assets/scenes/maps/Riverside/riverside.scene','Tools/riverside_map.py'},changed
baseline={p:sha(ROOT/p) for p in guard}
(OUT/'install-baseline.json').write_text(json.dumps(dict(files=baseline,preexisting_changed_files=changed),indent=2))
public=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl'
original=public.read_text();assert 'drinks-fridge-v1/' not in original,'Already installed: inspect the receipt'
before=OUT/'install-before';before.mkdir(exist_ok=True);(before/public.name).write_bytes(public.read_bytes())
preview=(ROOT/'Assets/models/maps/riverside/drinks-fridge-v1/store_without_fridge.vmdl').read_text()
own=(ROOT/'Assets/models/maps/riverside/drinks-fridge-v1/drinks_fridge.vmdl').read_text()
pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group();oldnode=re.search(pattern,preview,re.S).group()
merged=preview.replace(oldnode,oldnode+'\n'+node,1)
names=lambda text:set(re.findall(r'from = "([^"]+)"',text))
assert not names(own)&names(original),'Material remap collision'
remaps=re.findall(r'\{ from = "[^\n]+?\}',own)
index=merged.index('\t'*7+'{ from = ')
merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
stage=OUT/'install-stage';target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
plan=dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files={str(public.relative_to(ROOT)).replace('\\','/'):sha(target)})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
build=(HERE/'build.py').read_text(encoding='utf-8');body=build[build.index('m=K.Model();X='):build.index('count=K.write_model')]
body=body.replace("for p,_,_,_ in colours","for p in ('enamel','liner','frame','steel','red','blue','green','label')")
helper='''"""Approved Riverside porch drinks fridge; preserve the legacy light and collider."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
MAT="materials/riverside/drinks-fridge-v1"
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    return m

def append_to(target):
    import riverside_parts as P
    legacy=K.Model()
    P.fridge(legacy,(96.,560.),(0.,-1.),20.)
    target.boxes.extend(legacy.boxes)
    target.hulls.extend(legacy.hulls)
    m=model()
    for paint,faces in m.polygons.items():
        alias="rsvf_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/riverside_drinks_fridge.py').write_text(helper,encoding='utf-8')
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import riverside_drinks_fridge as F;import riverside_parts as P
proof=OUT/'approved-generator.obj';K.write_obj(proof,F.model(),'drinks_fridge')
assert proof.read_text().splitlines()[3:]==(ROOT/'Assets/models/maps/riverside/drinks-fridge-v1/drinks_fridge.obj').read_text().splitlines()[3:]
old=K.Model();P.fridge(old,(96.,560.),(0.,-1.),20.);lights_before=len(P.LIGHTS)
test=K.Model();F.append_to(test)
assert len(test.boxes)==len(old.boxes) and len(test.hulls)==len(old.hulls)
assert len(P.LIGHTS)==lights_before+1
assert K.vec3(test.boxes[0][0])==K.vec3(old.boxes[0][0])
generator=ROOT/'Tools/riverside_map.py';g=generator.read_text(encoding='utf-8');(before/generator.name).write_bytes(generator.read_bytes())
old='    P.fridge( m, ( e0 + 26, PORCH_N0 + 40 ), ( 0, -1 ), F )';assert g.count(old)==1
g=g.replace(old,'''    from riverside_drinks_fridge import append_to as append_approved_porch_fridge
    append_approved_porch_fridge( m )''')
generator.write_text(g,encoding='utf-8')
script=(ROOT/'Sources/Railhead/road-barrier-v1/install.cs.txt').read_text().replace('output/railhead/road-barrier-v1','output/riverside/drinks-fridge-v1').replace('Assets/models/maps/railhead/','Assets/models/maps/riverside/').replace('InstalledBarriers=1','InstalledFridges=1')
(HERE/'install.cs.txt').write_text(script,encoding='utf-8')
print(json.dumps(dict(public_asset=str(public.relative_to(ROOT)),generator_matches_approved=True,fridges=1,legacy_light_preserved=True)))
