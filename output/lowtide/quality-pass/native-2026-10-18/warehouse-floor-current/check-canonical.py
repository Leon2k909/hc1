"""Regenerate into review output and compare with the native imported resources."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_floor_surfaces as S
import lowtide_interior as I
import lowtide_map as L
import map_kit as K
from lowtide_material_stage import remaps
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

promotion=json.loads((OUT/'promotion.json').read_text())
stage=OUT/'canonical'
resources=S.write_materials(stage)
assert len(resources)==9
exact={p:sha(stage/p)==sha(ROOT/'Assets'/p) for p in promotion['resources']}
assert all(exact.values()),exact
# Exercise the actual map's warehouse builder; configure must only change the
# two existing bindings after the ordinary interior material setup.
warehouse,_=L.half()
L.configure(warehouse)
before=dict(warehouse.material_overrides)
paint_counts={k:len(v) for k,v in warehouse.polygons.items()}
S.configure(warehouse)
changes={k:(before.get(k),v) for k,v in warehouse.material_overrides.items() if before.get(k)!=v}
assert set(changes)=={'floorboards','rw_concrete'}
assert paint_counts=={k:len(v) for k,v in warehouse.polygons.items()}
assert warehouse.tile_overrides['rw_concrete']==256.0
L.WINDOWS.configure(warehouse)
for side in ('east','west'):
    rows=remaps((ROOT/f'Assets/models/maps/lowtide/lowtide_{side}.vmdl').read_bytes())
    for slot,path in warehouse.material_overrides.items():
        if slot+'.vmat' in rows:
            assert rows[slot+'.vmat'][0]==path,(side,slot,path,rows[slot+'.vmat'][0])
result={'resource_files_exact':len(exact),'binding_changes':changes,'warehouse_polygons_unchanged':True,
        'live_assets_written':False,'source_atlas_unchanged':sha(S.F.SOURCE/'warehouse-boards-source.png')==sha(ROOT/'Assets'/S.F.RESOURCE/'warehouse_color.png')}
(OUT/'canonical-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
