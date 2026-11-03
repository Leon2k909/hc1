"""Integrate the approved preview without rebuilding unrelated map geometry."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/railhead/clock-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
check=json.loads((OUT/'validation.json').read_text());assert check['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());assert all(sha(ROOT/p)==h for p,h in guard.items())
before=OUT/'install-before';before.mkdir(exist_ok=True)
public=ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl'
original=public.read_text();assert 'clock-v1/' not in original,'Already installed; inspect before retrying'
(before/public.name).write_bytes(public.read_bytes())
preview=(ROOT/'Assets/models/maps/railhead/clock-v1/dressing_without_clock.vmdl').read_text()
own=(ROOT/'Assets/models/maps/railhead/clock-v1/station_clock.vmdl').read_text()
pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group();oldnode=re.search(pattern,preview,re.S).group()
merged=preview.replace(oldnode,oldnode+'\n'+node,1)
remaps=re.findall(r'\{ from = "[^\n]+?\}',own)
marker='\t'*7+'{ from = ';index=merged.index(marker)
merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
physics='_class = "PhysicsShapeList"'
assert original[original.index(physics):]==merged[merged.index(physics):]
stage=OUT/'install-stage';target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
plan=dict(before={str(public.relative_to(ROOT)).replace('\\','/'):sha(public)},files={str(public.relative_to(ROOT)).replace('\\','/'):sha(target)})
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
# The generator retains identical approved geometry and the old clock's collision.
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();Z='):build.index('count=K.write_model')]
helper='"""Approved central-platform station clock; render geometry only."""\nimport math\nimport numpy as np\nimport map_kit as K\nimport riverdale_parts as G\nMAT="materials/railhead/clock-v1"\ndef model():\n'+''.join('    '+l+'\n' for l in body.splitlines())+'    return m\n\ndef append_to(target):\n    m=model()\n    for paint,faces in m.polygons.items():\n        alias="rh_sc_"+paint\n        target.material_overrides[alias]=m.material_overrides[paint]\n        target.tile_overrides[alias]=m.tile_overrides[paint]\n        for i,(points,normal) in enumerate(faces):\n            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))\n'
(ROOT/'Tools/railhead_station_clock.py').write_text(helper)
sys.path.insert(0,str(ROOT/'Tools'));import railhead_station_clock as SC;import map_kit as K
proof=OUT/'approved-generator.obj';K.write_obj(proof,SC.model(),'station_clock')
assert proof.read_text().splitlines()[3:]==(ROOT/'Assets/models/maps/railhead/clock-v1/station_clock.obj').read_text().splitlines()[3:]
generator=ROOT/'Tools/railhead_map.py';g=generator.read_text();(before/generator.name).write_bytes(generator.read_bytes())
old='    clock( m, 0.0, 1110.0, 240.0, "n" )';assert g.count(old)==1
g=g.replace(old,'    # Approved 14:03 clock: keep the legacy housing collision.\n    from railhead_station_clock import append_to as append_station_clock\n    legacy_clock = K.Model()\n    clock( legacy_clock, 0.0, 1110.0, 240.0, "n" )\n    legacy_clock.polygons.clear()\n    m.extend( legacy_clock )\n    append_station_clock( m )')
# railhead_map imports map_kit as MK, verified below; use its actual alias.
import_line=next(l for l in g.splitlines() if l.startswith('import map_kit as '));alias=import_line.split()[-1]
g=g.replace('legacy_clock = K.Model()',f'legacy_clock = {alias}.Model()')
generator.write_text(g)
script=(ROOT/'Sources/Lowtide/quay-ladder-v1/install.cs.txt').read_text().replace('output/lowtide/quay-ladder-v1','output/railhead/clock-v1').replace('Assets/models/maps/lowtide/','Assets/models/maps/railhead/').replace('InstalledLadders=6','InstalledClocks=1')
(HERE/'install.cs.txt').write_text(script)
print(json.dumps(dict(files=plan['files'],generator_matches_approved=True)))
