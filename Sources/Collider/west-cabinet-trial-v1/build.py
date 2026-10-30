"""Replace the actual west cabinet placeholder with a review-only fabricated rack."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_server_rack as SR

OUT=ROOT/'output/asset-improvement-20261029/west-cabinet'
RESOURCE='models/props/collider/west-cabinet-trial-v1'
DEST=ROOT/'Assets'/RESOURCE
ORIGIN=np.array((-430.,80.,0.))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def baseline():
    m=K.Model();vertices=[];uv=[];normals=[];paint='';counts=Counter()
    for line in (ROOT/'Assets/models/maps/collider/collider_detail.obj').read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]]
            points=np.array([vertices[v] for v,t,n in ids])
            if np.all(points>=(-458,45,-.1)) and np.all(points<=(-402,115,139)):
                m.polygon(paint,[p-ORIGIN for p in points],uv=[uv[t] for v,t,n in ids],
                    normals=[normals[n] for v,t,n in ids]);counts[paint]+=1
    assert dict(counts)=={'co_beam':132,'co_case':12,'co_trim':132},counts
    m.box((-24,-30,0),(24,30,138),None,'metal')
    M.configure(m)
    return m,dict(counts)


def candidate():
    source=K.Model();SR.build(source,0,0,collision=False)
    scale=np.array((48/28,60/44,138/84))
    m=K.Model()
    for paint,polys in source.polygons.items():
        for i,(points,normal) in enumerate(polys):
            normals=source.polygon_normals.get((paint,i))
            m.polygon(paint,[p*scale for p in points],
                uv=source.polygon_uvs.get((paint,i)),
                normals=None if normals is None else [K.normalise(n/scale) for n in normals])
    m.box((-24,-30,0),(24,30,138),None,'metal')
    M.configure(m)
    return m


def main():
    assert not DEST.exists() or not any(DEST.iterdir()),'Candidate already exists'
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'Assets/models/maps/collider'/('collider_detail'+ext) for ext in ('.obj','.mtl','.vmdl')]
    protected.append(ROOT/'Assets/scenes/maps/Collider/collider.scene')
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    before,counts=baseline();after=candidate();models={}
    for name,m in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),m,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,m)
        positions=np.array([p for polys in m.polygons.values() for ps,n in polys for p in ps])
        models[name]={'triangles':m.triangle_count(),'sourceSHA256':sha(DEST/(name+'.obj')),
            'boundsPlan':[positions.min(0).tolist(),positions.max(0).tolist()]}
    for path,expected in guards.items():assert sha(ROOT/path)==expected,path
    result={'status':'candidate-only-not-installed','editorUsed':False,'engineCompilation':'pending',
        'baselinePlanPosition':ORIGIN.tolist(),'originalTriangleMaterials':counts,
        'baselineCopiedFromInstalledGeometry':True,'sameAuthoredCollisionInches':[48,60,138],
        'models':models,'protectedSourceSHA256':guards,
        'design':'Fabricated rack style from Collider east cabinet, fitted to the existing west cover envelope',
        'previewRenderer':'Offline Blender Cycles, matched camera/lighting/scale'}
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'candidate.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
