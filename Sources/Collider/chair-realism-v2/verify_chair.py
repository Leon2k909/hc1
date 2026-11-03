from pathlib import Path
import re, json, hashlib
import numpy as np

WORK=Path(__file__).resolve().parent
ROOT=Path(r'C:/sbox-projects/hc1/forked-shooter-main')
ASSETS=WORK/'candidate/Assets'
report={}
for label,folder in [('before','chair-trial-v1'),('after','chair-realism-v2')]:
    path=ASSETS/f'models/props/collider/{folder}/after.obj'
    vs=[];ts=[];ns=[];faces=[];paint='';paints=set()
    for line in path.read_text().splitlines():
        if line.startswith('v '):vs.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):ts.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):ns.append(list(map(float,line.split()[1:])))
        elif line.startswith('usemtl '):paint=line[7:];paints.add(paint)
        elif line.startswith('f '):faces.append([[int(a)-1 for a in token.split('/')] for token in line.split()[1:]])
    v=np.array(vs);t=np.array(ts);n=np.array(ns);f=np.array(faces)
    assert np.isfinite(v).all() and np.isfinite(t).all() and np.isfinite(n).all()
    assert f.min()>=0 and f[:,:,0].max()<len(v) and f[:,:,1].max()<len(t) and f[:,:,2].max()<len(n)
    pos=v[f[:,:,0]]
    area=np.linalg.norm(np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),axis=1)/2
    assert (area>1e-10).all(),(label,'degenerate triangles',int((area<=1e-10).sum()))
    assert ((np.linalg.norm(n,axis=1)>.99)&(np.linalg.norm(n,axis=1)<1.01)).all()
    if label=='after':
        alignment=np.einsum('ij,ij->i',np.cross(pos[:,1]-pos[:,0],pos[:,2]-pos[:,0]),n[f[:,:,2]].mean(axis=1))
        assert (alignment>=-1e-10).all(),('inverted faces',int((alignment< -1e-10).sum()))
    doc=path.with_suffix('.vmdl').read_text()
    maps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',doc))
    for p in paints:
        mat=ASSETS/maps[p+'.vmat'];assert mat.is_file(),mat
        for texture in re.findall(r'Texture\w+\s+"([^"]+)"',mat.read_text()):
            if not texture.startswith('materials/default/') and not texture.startswith('['):assert (ASSETS/texture).is_file(),texture
    report[label]={'triangles':len(f),'materials':len(paints),'finiteAttributes':True,'validIndices':True,'nondegenerateTriangles':True,'unitNormals':True,'resolvedMaterialTextures':True,'boundsOBJ':{'min':v.min(axis=0).tolist(),'max':v.max(axis=0).tolist()},'objSHA256':hashlib.sha256(path.read_bytes()).hexdigest()}
guard=json.loads((WORK/'protected.json').read_text())
changed=[p for p,h in guard.items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
assert not changed,changed
report['protectedOriginalFilesUnchanged']=len(guard)
for label,folder in [('before','chair-trial-v1'),('after','chair-realism-v2')]:
    doc=(ASSETS/f'models/props/collider/{folder}/after.vmdl').read_text()
    suffix=doc[doc.index('_class = "PhysicsShapeList"'):]
    report[label]['collisionSuffixSHA256']=hashlib.sha256(suffix.encode()).hexdigest()
assert report['before']['collisionSuffixSHA256']==report['after']['collisionSuffixSHA256']
report['collisionExactlyPreserved']=True
report['engineCompilation']='not run; offline review candidate'
(WORK/'candidate/verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
