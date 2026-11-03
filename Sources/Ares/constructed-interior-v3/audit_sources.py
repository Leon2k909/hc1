from pathlib import Path
import json,sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text())
stack=list(scene['GameObjects']);models=[]
while stack:
    g=stack.pop();stack.extend(g.get('Children',[]))
    for c in g.get('Components',[]):
        if c.get('__type')=='Sandbox.ModelRenderer' and 'ares' in str(c.get('Model')):
            models.append((g.get('Name'),c))
print(json.dumps([m for m in models if m[1].get('Model',{}).get('Path','').endswith(('ares_hall.vmdl','ares_reactor.vmdl','ares_backdrop.vmdl'))],indent=2))
_,faces=S.read_obj(ROOT/'output/ares/surface-finish-v2/stage/Assets/models/maps/ares/surface-finish-v2/hall_trial.obj')
flat=[(m,[tuple(map(float,p.split())) for p,uv,n in c]) for m,c in faces if all(abs(float(p.split()[1]))<.0001 for p,uv,n in c)]
print('Floor triangles by material:',Counter(m for m,c in flat))
print('Other top surfaces:',[(m,[min(p[i] for p in c) for i in (0,2)],[max(p[i] for p in c) for i in (0,2)]) for m,c in flat if m not in ('ar_in_floor','ar_in_dark')][:35])
