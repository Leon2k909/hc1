import json, sys
import numpy as np
import native

manifest=json.loads((native.OUT/'manifest.json').read_text())
views=[]
for index,name,distance in [(1,'hero',27),(1,'context',80),(8,'south',30)]:
    p=manifest['placements'][index]
    c=np.array(p['centre'])
    x=np.array(p['target'])-c; x/=np.linalg.norm(x)
    y=np.cross([0,0,1],x); y/=np.linalg.norm(y)
    eye=c+x*distance*.82+y*distance*.57+np.array([0,0,distance*.21])
    target=c+np.array(p['out'])*-2+np.array([0,0,.8])
    views.append(dict(name=name,eye=list(eye),target=list(target),fov=62))
(native.OUT/'capture-config.json').write_text(json.dumps(dict(views=views),indent=2)+'\n')
if '--rear' in sys.argv:
    p=manifest['placements'][1]; c=np.array(p['centre'])
    x=np.array(p['target'])-c; x/=np.linalg.norm(x)
    y=np.cross([0,0,1],x); y/=np.linalg.norm(y)
    views=[dict(name='rear',eye=list(c-x*9+y*24+np.array([0,0,10])),target=list(c+np.array([0,0,1.5])),fov=65)]
    (native.OUT/'capture-config.json').write_text(json.dumps(dict(views=views),indent=2)+'\n')
print(json.dumps(views,indent=2))
