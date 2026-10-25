"""Export only the lock and a small sample of its existing door joinery for review."""
from pathlib import Path
import sys
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_detail as D
import belltower_padlock as P
import belltower_furniture as F

folder=ROOT/'output/belltower/quality/shed-padlock-v1-studio'
folder.mkdir(parents=True,exist_ok=True)
records=[]
for name in ('before','after'):
    model=K.Model()
    for x in (-3.85,1.075):
        F.bevel_box(model,(x,.66,-2),np.eye(3),(4.77,1.08,18),F.DARK,.09,4)
    F.bevel_box(model,(-4,1.5,2),np.eye(3),(18,1,3.5),F.WOOD,.16,5)
    F.bevel_box(model,(7,.62,-2),np.eye(3),(2,1.24,18),F.WOOD,.14,6)
    if name=='before':P.old_handle(model,(0,0,0),np.eye(3),7)
    else:P.build(model,(0,0,0),np.eye(3),7)
    D.configure(model)
    K.write_obj(folder/(name+'.obj'),model,name)
    materials={paint:model.material_overrides.get(paint,'materials/buildings/'+paint+'.vmat') for paint in model.polygons}
    if P.STEEL in materials:
        materials[P.STEEL]=str(ROOT/'output/belltower/shed-padlock-v1/stage/Assets'/P.STEEL_MATERIAL)
    records.append({'name':name,'materials':materials,
                    'review_bounds':[[0,-11,-6],[5,4,6]],'camera_offset':[1.5,.7,.25]})
(folder/'models.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps({'exported':len(records),'kind':'offline construction preview; not an engine screenshot'}))
