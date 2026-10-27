import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import forestbase_map as M
import numpy as np
rows=[]
for i,(lo,hi) in enumerate(M.boundary_boxes()):
    lo,hi=np.array(lo),np.array(hi)
    rows.append(M.go(f'Boundary Clip {i}',f'clip/{i}',(lo+hi)/2,
                    comps=[M.collider(f'clip/{i}/box',np.abs(M.K.to_world(hi-lo)),False)],tags='playerclip'))
target=Path(__file__).with_name('boundary-plan.json')
target.write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(dict(boxes=len(rows),path=str(target))))
