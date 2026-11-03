"""Check only the installed clock hook, without rebuilding the shared map."""
from pathlib import Path
import json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import railhead_map as R
import railhead_station_clock as SC
old=K.Model();R.clock(old,0.,1110.,240.,'n')
target=K.Model()
source=(ROOT/'Tools/railhead_map.py').read_text()
start=source.index('    # Approved 14:03 clock:');end=source.index('    kiosk( m, KIOSKS[2] )',start)
snippet='\n'.join(l[4:] for l in source[start:end].splitlines())
exec(snippet,dict(K=K,clock=R.clock,m=target))
assert len(target.boxes)==len(old.boxes)==1 and len(target.hulls)==len(old.hulls)==0
for actual,wanted in zip(target.boxes,old.boxes):
 for a,b in zip(actual[:3],wanted[:3]):assert np.array_equal(a,b)
 assert actual[3]==wanted[3]
R.configure(target)
assert all(path.startswith('materials/railhead/clock-v1/') or path=='materials/railhead/rw_case_glass.vmat' for path in target.material_overrides.values())
report=dict(generator_hook_checked=True,legacy_collision_preserved=True,private_materials_preserved=True)
(ROOT/'output/railhead/clock-v1/generator-check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
