import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_structure as S

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
S.write_materials(HERE/'selected')
baseline=json.loads((HERE/'manifest.json').read_text())
for relative,expected in baseline['protected'].items():
    assert digest(ROOT/relative)==expected, relative
resources={p.relative_to(HERE/'selected').as_posix():digest(p) for p in sorted((HERE/'selected').rglob('*')) if p.is_file()}
for relative,expected in resources.items():
    compare=relative.replace('lt_cast_iron_v2.vmat','lt_cast_paint_trial.vmat') if relative==S.IRON else relative
    assert digest(ROOT/'Assets'/compare)==expected, relative
mapping={'materials/lowtide/lt_timber.vmat':S.TIMBER,'materials/buildings/iron_black.vmat':S.IRON}
models=[]
for bank in ('east','west'):
    relative=f'models/maps/lowtide/lowtide_{bank}.vmdl'
    before=(ROOT/'Assets'/relative).read_bytes()
    after=before
    for old,new in mapping.items():
        token=f'to = "{old}"'.encode()
        assert after.count(token)==1
        after=after.replace(token,f'to = "{new}"'.encode())
    back=after
    for old,new in mapping.items(): back=back.replace(f'to = "{new}"'.encode(),f'to = "{old}"'.encode())
    assert back==before
    target=HERE/'selected'/relative; target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(after)
    models.append({'path':relative,'before':hashlib.sha256(before).hexdigest(),'after':digest(target),'remaps':2,'materialSlots':len(re.findall(rb'from = "',before)),'onlyTwoMaterialPathsChanged':True})
report={'resources':resources,'models':models,'protected':baseline['protected'],
        'paintDependencies':{f'Assets/materials/lowtide/marine/paint_{n}.png':digest(ROOT/f'Assets/materials/lowtide/marine/paint_{n}.png') for n in ('color','normal','rough')},
        'selected':'continuous timber + painted iron','reviewedCaptures':18,'productionBound':False}
(HERE/'promotion-plan.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'resourcesExact':len(resources),'models':models},indent=2))
