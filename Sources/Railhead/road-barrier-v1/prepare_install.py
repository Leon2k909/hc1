"""Install only the approved east-yard barrier, preserving current shared work."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/road-barrier-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'validation.json').read_text())['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text())
changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
public=ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl'
original=public.read_text();assert 'road-barrier-v1/' not in original,'Already installed; inspect the receipt instead of retrying'
before=OUT/'install-before';before.mkdir(exist_ok=True);(before/public.name).write_bytes(public.read_bytes())
preview=(ROOT/'Assets/models/maps/railhead/road-barrier-v1/east_without_barrier.vmdl').read_text()
own=(ROOT/'Assets/models/maps/railhead/road-barrier-v1/road_barrier.vmdl').read_text()
pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group();oldnode=re.search(pattern,preview,re.S).group()
merged=preview.replace(oldnode,oldnode+'\n'+node,1)
remaps=re.findall(r'\{ from = "[^\n]+?\}',own)
names=lambda text:set(re.findall(r'from = "([^"]+)"',text))
assert not names(own)&names(original),'Material remap collision: use a distinct alias before integrating'
marker='\t'*7+'{ from = ';index=merged.index(marker)
merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
physics='_class = "PhysicsShapeList"';assert original[original.index(physics):]==merged[merged.index(physics):]
stage=OUT/'install-stage';target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
plan=dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files={str(public.relative_to(ROOT)).replace('\\','/'):sha(target)})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
# Retain the approved geometry in the east-only generator hook. Other barrier
# placements still use their existing helper.
build=(HERE/'build.py').read_text(encoding='utf-8');body=build[build.index('m=K.Model();F='):build.index('count=K.write_model')]
helper='''"""Approved east-yard roadworks barrier; render geometry only."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
MAT="materials/railhead/road-barrier-v1"
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    return m

def append_to(target):
    m=model()
    for paint,faces in m.polygons.items():
        alias="rh_rb_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/railhead_road_barrier.py').write_text(helper,encoding='utf-8')
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import railhead_road_barrier as B
proof=OUT/'approved-generator.obj';K.write_obj(proof,B.model(),'road_barrier')
assert proof.read_text().splitlines()[3:]==(ROOT/'Assets/models/maps/railhead/road-barrier-v1/road_barrier.obj').read_text().splitlines()[3:]
assert not B.model().boxes and not B.model().hulls
generator=ROOT/'Tools/railhead_map.py';g=generator.read_text(encoding='utf-8');(before/generator.name).write_bytes(generator.read_bytes())
old='    detail( "road_barrier", m, s * 1905.0, -1556.0, "e" )';assert g.count(old)==1
g=g.replace(old,'''    if s > 0:
        from railhead_road_barrier import append_to as append_approved_barrier
        append_approved_barrier( m )
    else:
        detail( "road_barrier", m, s * 1905.0, -1556.0, "e" )''')
generator.write_text(g,encoding='utf-8')
script=(ROOT/'Sources/Lowtide/quay-ladder-v1/install.cs.txt').read_text().replace('output/lowtide/quay-ladder-v1','output/railhead/road-barrier-v1').replace('Assets/models/maps/lowtide/','Assets/models/maps/railhead/').replace('InstalledLadders=6','InstalledBarriers=1')
(HERE/'install.cs.txt').write_text(script,encoding='utf-8')
print(json.dumps(dict(public_asset=str(public.relative_to(ROOT)),generator_matches_approved=True,barriers=1)))
