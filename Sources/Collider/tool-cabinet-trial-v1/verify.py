"""Check exported mesh/materials and actual exported compound collision, offline."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import psutil
process=psutil.Process();process.nice(psutil.IDLE_PRIORITY_CLASS);process.cpu_affinity(process.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import hashlib,json,math,re,sys
import numpy as np
from scipy.spatial import ConvexHull,cKDTree

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
HERE=Path(__file__).parent;OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet'
DEST=ROOT/'Assets/models/props/collider/tool-cabinet-trial-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def obj(path):
    vs=[];uv=[];ns=[];faces=[];paint='';groups=[];current=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z));current.append((-a,n,z))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append((-a,n,z))
        elif line.startswith(('o ','g ')):
            if current:groups.append(current);current=[]
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):faces.append((paint,[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]))
    if current:groups.append(current)
    return np.array(vs),np.array(uv),np.array(ns),faces,groups


def hull_parts(path):
    vertices,_,_,faces,_=obj(path)
    parent=list(range(len(vertices)));used=set()
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    for paint,face in faces:
        ids=[v[0] for v in face];used.update(ids)
        for i in ids[1:]:parent[root(i)]=root(ids[0])
    components={}
    for i in sorted(used):components.setdefault(root(i),[]).append(i)
    # HullPerElement is based on disconnected face topology, not OBJ object names.
    return [vertices[ids] for ids in sorted(components.values(),key=min)]


def main():
    d=json.loads((HERE/'candidate.json').read_text())
    for p,h in d['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p
    reports={}
    for name in ('before','after'):
        path=DEST/(name+'.obj');assert sha(path)==d['models'][name]['meshSHA256']
        vs,uv,ns,faces,_=obj(path)
        assert np.isfinite(vs).all() and np.isfinite(uv).all() and np.isfinite(ns).all()
        assert np.max(abs(np.linalg.norm(ns,axis=1)-1))<.0015
        bad=[]
        for paint,ids in faces:
            assert len(ids)==3
            points=np.array([vs[v] for v,t,n in ids]);cross=np.cross(points[1]-points[0],points[2]-points[0])
            assert np.linalg.norm(cross)>.000001,(name,paint,'degenerate')
            if cross@np.mean([ns[n] for v,t,n in ids],axis=0)<-1e-5:bad.append(paint)
            assert all(0<=v<len(vs) and 0<=t<len(uv) and 0<=n<len(ns) for v,t,n in ids)
        assert not bad,(name,'winding',Counter(bad))
        assert len(faces)==d['models'][name]['triangles']
        remaps=dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',(DEST/(name+'.vmdl')).read_text()))
        textures=set()
        for paint in {p for p,f in faces}:
            mat=ROOT/'Assets'/remaps[paint+'.vmat'];assert mat.is_file(),mat
            for tex in re.findall(r'Texture\w+\s+"([^"]+)"',mat.read_text()):
                if tex.startswith('[') or tex.startswith('materials/default/'):continue
                assert (ROOT/'Assets'/tex).is_file(),tex;textures.add(tex)
        reports[name]={'triangles':len(faces),'degenerateTriangles':0,'windingErrors':0,
                       'finiteUVsAndUnitNormals':True,'materials':len(remaps),'textures':len(textures),
                       'boundsInches':[vs.min(axis=0).tolist(),vs.max(axis=0).tolist()]}
        if name=='before':old_bounds=(vs.min(axis=0),vs.max(axis=0))
        else:vertices=vs
    assert np.all(vertices.min(axis=0)>=old_bounds[0]-.01)
    assert np.all(vertices.max(axis=0)<=old_bounds[1]+.01)
    # Check that ModelDoc actually references the authored hulls and boxes.
    doc=(DEST/'after.vmdl').read_text()
    expected_boxes=[s for s in d['collisionShapes'] if s['kind'] in ('box','oriented-box')]
    actual_boxes=re.findall(r'\{\s*_class = "PhysicsShapeBox"[\s\S]*?\n\s*\}',doc)
    assert len(actual_boxes)==len(expected_boxes)
    for block,s in zip(actual_boxes,expected_boxes):
        values={k:np.fromstring(v,sep=',') for k,v in re.findall(r'(origin|angles|dimensions) = \[([^]]+)\]',block)}
        if s['kind']=='box':
            lo,hi=np.array(s['lo']),np.array(s['hi']);centre=(lo+hi)/2;size=hi-lo;axes=np.eye(3)
        else:centre=np.array(s['centre']);size=np.array(s['size']);axes=np.array(s['axes'])
        assert np.allclose(values['origin'],K.to_world(centre),atol=.00011)
        assert np.allclose(values['dimensions'],size,atol=.00011)
        assert np.allclose(values['angles'],K.angles_of([K.to_world(a) for a in axes]),atol=.00011)
    exported_hulls=[]
    for file in re.findall(r'filename = "([^"]+_hulls_[^"]+\.obj)"',doc):
        path=ROOT/'Assets'/file;assert path.is_file()
        exported_hulls.extend(hull_parts(path))
    expected_hulls=[s['points'] for surface in sorted({s['surface'] for s in d['collisionShapes'] if s['kind']=='hull'})
                    for s in d['collisionShapes'] if s['kind']=='hull' and s['surface']==surface]
    assert len(exported_hulls)==len(expected_hulls)
    for actual,expected in zip(exported_hulls,expected_hulls):
        extreme=np.array(expected)[ConvexHull(expected).vertices]
        assert cKDTree(actual).query(extreme)[0].max()<.001
        assert cKDTree(expected).query(actual)[0].max()<.001
    # Reconstruct the exported bodies for probes; do not test a separate idealised shape.
    shapes=[];all_points=[]
    for points in exported_hulls:
        hull=ConvexHull(points);shapes.append(hull.equations);all_points.extend(points)
    for s in expected_boxes:
        if s['kind']=='box':
            lo,hi=np.array(s['lo']),np.array(s['hi']);centre=(lo+hi)/2;size=hi-lo;axes=np.eye(3)
        else:centre=np.array(s['centre']);size=np.array(s['size']);axes=np.array(s['axes'])
        points=np.array([centre+np.array((a,b,c))*size/2@axes for a in (-1,1) for b in (-1,1) for c in (-1,1)])
        shapes.append(ConvexHull(points).equations);all_points.extend(points)
    def solid(p):return any(np.max(eq[:,:3]@np.array(p)+eq[:,3])<.001 for eq in shapes)
    probes=[('open underside',(0,0,6),False),('below cabinet',(0,0,10.5),False),
            ('closed drawer cabinet',(0,0,29),True),('worktop',(0,0,49),True),
            ('space behind drawer grip',(0,-20.55,18.55),False),('drawer grip',(0,-21.3,18.55),True),
            ('space behind push grip',(38.6,0,40),False),('push grip',(39.5,0,40),True)]
    for i,w in enumerate(d['wheels']):
        c=np.array(w['centre']);probes.extend([(f'wheel {i} centre',c.tolist(),True),(f'wheel {i} ground',(c-UP*4.2).tolist(),True)])
    for axis in (0,1):
        for sign in (-1,1):
            for z in (2,8,18,35,48):
                p=np.array((0.,0.,z));p[axis]=sign*(44 if axis==0 else 25)
                probes.append(('outside existing footprint',p.tolist(),False))
    for name,p,expected in probes:assert solid(p)==expected,(name,p,expected)
    points=np.array(all_points);dist=cKDTree(vertices).query(points)[0]
    assert dist.max()<.70,('collision protrusion from visible geometry',float(dist.max()))
    assert abs(vertices[:,2].min())<.001 and abs(points[:,2].min())<.001
    assert np.all(points.min(axis=0)>=old_bounds[0]-.01) and np.all(points.max(axis=0)<=old_bounds[1]+.01)
    # Player-width clearance outside each side; no hidden body extends into that lane.
    for axis,distance in ((0,58),(1,40)):
        for sign in (-1,1):
            centre=np.zeros(3);centre[axis]=sign*distance
            assert all(np.linalg.norm(q[:2]-centre[:2])>16 for q in points)
    result={'installedInMap':False,'originalRetained':True,'protectedSourcesUnchanged':len(d['protectedSourceSHA256']),
            'variants':reports,'collisionBoxes':len(expected_boxes),'collisionHulls':len(exported_hulls),
            'checkedFromExportedModelDocAndHullFiles':True,'collisionProbeCount':len(probes),'allCollisionProbesPassed':True,
            'undersideAndHandleGapsClear':True,'allFourTyresTouchGround':True,'insideOriginalVisibleFootprint':True,
            'maximumCollisionVertexDistanceToVisibleVertexInches':round(float(dist.max()),4),
            'outsidePlayerWidthClearancePassed':True,'editorUsed':False,'nativeCollisionAndAppearance':'pending'}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


UP=np.array((0.,0.,1.))
if __name__=='__main__':main()
