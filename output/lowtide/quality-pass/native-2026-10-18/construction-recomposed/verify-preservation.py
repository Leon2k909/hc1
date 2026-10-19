"""Verify the new grate surfaces and pavement apertures survive composition."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_window_construction as W

OUT=Path(__file__).resolve().parent
m=json.loads((OUT/'manifest.json').read_text())
checks={}
for name in ('lowtide_east','lowtide_west','lowtide_finish'):
    relative=f'Assets/models/maps/lowtide/{name}.obj'
    current=W.face_keys((ROOT/relative).read_text(),attributes=True)
    staged=W.face_keys((OUT/'stage'/relative).read_text(),attributes=True)
    paints={'setts'} if name!='lowtide_finish' else {'lt_grate_cast_iron','lt_grate_well'}
    keep=lambda data:{k:v for k,v in data.items() if k[0] in paints}
    assert keep(current)==keep(staged),(name,'grate or paving attributes changed')
    checks[name]=dict(preserved_triangles=sum(keep(current).values()),materials=sorted(paints))
    del current,staged
drains=json.loads((ROOT/'output/lowtide/quality-pass/drain-construction/manifest.json').read_text())
dependencies={p:h for p,h in drains['sources'].items() if p.endswith('.png') or p.startswith('Assets/materials/')}
assert all(W.sha(ROOT/p)==h for p,h in dependencies.items())
assert all(W.sha(ROOT/p)==h for p,h in m['protected_models'].items())
assert all(W.sha(OUT/'stage'/p)==h for p,h in m['staged_files'].items())
report=dict(status='current_grates_and_pavement_preserved',models=checks,
    material_inputs_verified=dependencies,live_models_unchanged=True,
    manifest_sha256=W.sha(OUT/'manifest.json'),native_visual_acceptance=False)
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='material_inputs_verified'},indent=2))
