"""Remove export-rounding degenerates from the newly installed leaf."""
from pathlib import Path
import hashlib,json
import numpy as np
ROOT=Path.cwd();OUT=ROOT/'output/ares/sliding-pressure-leaf-20261031';asset=ROOT/'Assets/models/maps/ares/sliding-doors-v1/ares_sliding_leaf.obj'
report=json.loads((OUT/'installation.json').read_text());key=next(k for k in report['afterSHA256'] if k.replace('\\','/')=='Assets/models/maps/ares/sliding-doors-v1/ares_sliding_leaf.obj')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(asset)==report['afterSHA256'][key]
lines=asset.read_text().splitlines(keepends=True);vertices=[];keep=[];removed=0
for line in lines:
    p=line.split()
    if p and p[0]=='v':vertices.append(np.array(list(map(float,p[1:]))))
    elif p and p[0]=='f':
        pts=[vertices[int(x.split('/')[0])-1] for x in p[1:]]
        if np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0]))<=1e-8:removed+=1;continue
    keep.append(line)
assert removed==4
data=''.join(keep).encode();tmp=asset.with_name(asset.name+'.clean-incoming');tmp.write_bytes(data);tmp.replace(asset)
(OUT/'stage/ares_sliding_leaf.obj').write_bytes(data)
report['trianglesPerLeaf']-=removed;report['degenerateTrianglesRemoved']=removed;report['afterSHA256'][key]=sha(asset)
(OUT/'installation.json').write_text(json.dumps(report,indent=2));print(json.dumps({'removed':removed,'trianglesPerLeaf':report['trianglesPerLeaf']}))
