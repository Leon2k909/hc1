"""Compose the reviewed resources and current four material bindings only."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT/'Tools'))
from lowtide_material_stage import remaps
OUT=Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

manifest=json.loads((OUT/'manifest.json').read_text())
fix=json.loads((OUT/'native-fix.json').read_text())
protected=dict(manifest['protected'])
assert protected[fix['source']]==fix['before']
protected[fix['source']]=fix['after']
assert all(sha(ROOT/p)==h for p,h in protected.items()), 'Current inputs changed'
resources={p:h for p,h in manifest['assets'].items() if not p.endswith('.vmdl')}
resources[fix['target'].removeprefix('Assets/')]=fix['after']
assert len(resources)==18
assert all(sha(ROOT/'Assets'/p)==h for p,h in resources.items()), 'Imported resources changed'
models={}
for relative in manifest['models']:
    current=ROOT/'Assets'/relative
    original=current.read_bytes()
    data=original
    changes=[p for p in manifest['material_remap_plan'] if p['model']==relative]
    assert len(changes)==2
    for change in changes:
        row=remaps(data)[change['slot']]
        assert row[0]==change['before']
        new=row[1].replace(change['before'].encode(),change['after'].encode())
        data=data.replace(row[1],new,1)
    target=OUT/'promotion'/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
    reverse=data
    for change in changes:
        reverse=reverse.replace(remaps(reverse)[change['slot']][1],remaps(original)[change['slot']][1],1)
    assert reverse==original
    models[relative]={'before':sha(current),'after':sha(target)}
result=dict(status='native_review_accepted_pending_model_import',protected=protected,resources=resources,
    models=models,material_remap_plan=manifest['material_remap_plan'],native_shader_fix=fix,
    reviewed_captures=24,review={'timber':'Dry, muted long boards; credible grain and orientation across joists. No error shader or visible normal reversal.',
    'concrete':'Restrained dust and traffic variation; no continuous painted-looking tire lines. Existing concrete detail retained.',
    'caveat':'East cargo was culled by corrupt compiled model bounds during review; both dressing assets rebuilt with finite bounds. Fresh production views required.'},
    geometry_changes=0,collision_changes=0,scene_changes=0,new_material_slots=0)
(OUT/'promotion.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(models=models,resources=len(resources),protected=len(protected)),indent=2))
