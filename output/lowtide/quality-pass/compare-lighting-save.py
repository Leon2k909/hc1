import json
from pathlib import Path
root=Path(__file__).resolve().parents[3]
a=json.loads((Path(__file__).parent/'warehouse-lighting-candidate.scene').read_text())
b=json.loads((root/'Assets/scenes/maps/Lowtide/lowtide.scene').read_text())
def differences(a,b,p=''):
    if a==b: return
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys()|b.keys(): differences(a.get(k),b.get(k),p+'/'+k)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)): differences(x,y,p+'/'+str(i))
    else: print(p,repr(a)[:180],'=>',repr(b)[:180])
differences(a,b)
