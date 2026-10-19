from pathlib import Path
import json

quality=Path('output/belltower/quality')
before=json.loads((quality/'daylight-v8/visual-scene.json').read_text())
after=json.loads(Path('Assets/scenes/maps/Belltower/belltower.scene').read_text())
def normalize(value):
    if isinstance(value,dict):
        if set(value)=={'Id','Path'}:
            return value['Path']
        return {key:normalize(item) for key,item in value.items()}
    if isinstance(value,list):
        return [normalize(item) for item in value]
    return value
differences=[]
def compare(a,b,path=''):
    if a==b:
        return
    if isinstance(a,dict) and isinstance(b,dict):
        for key in sorted(a.keys()|b.keys()):
            compare(a.get(key),b.get(key),path+'/'+key)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for index,(x,y) in enumerate(zip(a,b)):
            compare(x,y,path+'/'+str(index))
    else:
        differences.append({'path':path,'before':a,'after':b})
compare(normalize(before),normalize(after))
(quality/'daylight-v8-save/scene-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
print('Differences:',len(differences))
from collections import Counter
import numpy as np
def roundtrip(item):
    a,b=item['before'],item['after']
    if not isinstance(a,str) or not isinstance(b,str) or ',' not in a or ',' not in b:
        return False
    try:
        x=np.array(a.split(','),dtype=np.float32)
        y=np.array(b.split(','),dtype=np.float32)
        return x.shape==y.shape and np.allclose(x,y,atol=1e-6,rtol=0)
    except ValueError:
        return False
added=[d for d in differences if d['before'] is None]
changed=[d for d in differences if d['before'] is not None and not roundtrip(d)]
print('Added serialized defaults:',dict(Counter(d['path'].split('/')[-1] for d in added)))
print('Changed existing values:',json.dumps(changed,indent=2)[:13000])
