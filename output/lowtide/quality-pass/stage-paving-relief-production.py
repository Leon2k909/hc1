from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
FOLDER=ROOT/'output/lowtide/quality-pass'
STAGE=FOLDER/'paving-relief-production'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import lowtide_paving as P

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
initial=json.loads((FOLDER/'paving-relief-manifest.json').read_text())
for relative,digest in initial['protected'].items():
    assert sha(ROOT/relative)==digest, relative
K.ASSETS=STAGE
P.DIRECTORY=STAGE/'materials/lowtide'
P.SETTINGS=STAGE/'settings.json'
P.DIRECTORY.mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/'Tools/lowtide_paving_imagegen.json',P.SETTINGS)
P.bake_surface_maps()
P.write_materials()

# Full canonical regeneration must retain the accepted images and original
# colour/roughness, not merely reproduce an isolated helper's output.
for suffix in ('color','rough'):
    relative=f'materials/lowtide/lt_setts_{suffix}.png'
    assert sha(STAGE/relative)==sha(ROOT/'Assets'/relative), relative
for suffix in ('normal','height','ao'):
    relative=f'materials/lowtide/paving_relief/lt_setts_{suffix}.png'
    assert sha(STAGE/relative)==sha(ROOT/'Assets'/relative), relative
relative='materials/lowtide/lt_setts.vmat'
live=ROOT/'Assets'/relative
backup=FOLDER/'paving-relief-before/lt_setts.vmat'
backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists(): shutil.copy2(live,backup)
assert sha(backup)==sha(live)
protected={p:h for p,h in initial['protected'].items() if p!='Assets/'+relative}
manifest=dict(changes={relative:{'before':sha(live),'after':sha(STAGE/relative)}},protected=protected,
    canonical_regeneration={'original_colour_and_roughness_unchanged':True,'all_three_relief_maps_match':True},
    accepted_views=['paving-relief-'+v+'-candidate.png' for v in ('quay','close','grazing','west')])
(FOLDER/'paving-relief-production-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'changes':manifest['changes'],'protected_files':len(protected),'regeneration':manifest['canonical_regeneration']},indent=2))
