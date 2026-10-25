"""Inspect exported cascade geometry, including ledge occlusion and basin entry.

This does not compile shaders or establish native rendering/performance quality.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/forestbase'


def read_mesh(file):
    vertices=[];uvs=[];normals=[];faces=defaultdict(list);paint=None
    for line in file.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':
            x,z,n=map(float,fields[1:4]);vertices.append((-x,n,z))
        elif fields[0]=='vt':uvs.append(tuple(map(float,fields[1:3])))
        elif fields[0]=='vn':normals.append(tuple(map(float,fields[1:4])))
        elif fields[0]=='usemtl':paint=fields[1]
        elif fields[0]=='f':
            assert len(fields)==4
            faces[paint].append(tuple(tuple(int(n)-1 for n in v.split('/')) for v in fields[1:]))
    vertices=np.asarray(vertices);normals=np.asarray(normals)
    assert np.all(np.isfinite(vertices)) and np.all(np.isfinite(normals))
    assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=.005)
    for triangles in faces.values():
        indices=np.array([[v[0] for v in t] for t in triangles])
        p=vertices[indices]
        assert np.min(np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1))>1e-6
    return vertices,np.asarray(uvs),faces


def rock_triangles(mesh):
    vertices,uvs,faces=mesh
    return vertices[np.array([[v[0] for v in t] for t in faces['cascade_rock']])]


def signature(triangle):
    return tuple(map(tuple,triangle))


def occlusion(points,triangles):
    # Orthographic rays face north along the compound's principal view. A
    # smaller north coordinate puts opaque rock in front of the falling water.
    a,b,c=triangles[:,0],triangles[:,1],triangles[:,2]
    determinant=(b[:,2]-c[:,2])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,2]-c[:,2])
    valid=np.abs(determinant)>1e-7
    a,b,c,determinant=a[valid],b[valid],c[valid],determinant[valid]
    blocked=[]
    for offset in range(0,len(points),64):
        p=points[offset:offset+64]
        e,z=p[:,0,None],p[:,2,None]
        u=((b[:,2]-c[:,2])*(e-c[:,0])+(c[:,0]-b[:,0])*(z-c[:,2]))/determinant
        v=((c[:,2]-a[:,2])*(e-c[:,0])+(a[:,0]-c[:,0])*(z-c[:,2]))/determinant
        inside=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)
        north=u*a[:,1]+v*b[:,1]+(1-u-v)*c[:,1]
        front=np.min(np.where(inside,north,np.inf),axis=1)
        for k in np.flatnonzero(front<p[:,1]-2):
            blocked.append(dict(point=p[k].tolist(),rockNorth=float(front[k]),depth=float(p[k,1]-front[k])))
    return blocked


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,default=OUT/'terrace-stage')
    parser.add_argument('--baseline',type=Path,default=OUT/'terrace-before/Assets/models/maps/forestbase/vista.obj')
    args=parser.parse_args();file=args.candidate/'vista.obj'
    mesh=read_mesh(file)
    old=read_mesh(args.baseline)
    counts=Counter(signature(t) for t in rock_triangles(old))
    added=[]
    for triangle in rock_triangles(mesh):
        key=signature(triangle)
        if counts[key]:counts[key]-=1
        else:added.append(triangle)
    refitted_old_triangles=sum(counts.values())
    added=np.asarray(added)
    vertices,uvs,faces=mesh
    streams=[];probes=[];grids=[]
    for paint in sorted(p for p in faces if p.startswith('waterfall_') and p[-1].isdigit()):
        rows=defaultdict(dict)
        for triangle in faces[paint]:
            for vertex,uv,*normal in triangle:
                u,v=uvs[uv];rows[round(v,5)][round(u,5)]=vertices[vertex]
        ordered=[rows[v] for v in sorted(rows)]
        columns=sorted(ordered[0])
        assert all(sorted(r)==columns for r in ordered)
        grid=np.array([[r[u] for u in columns] for r in ordered])
        grids.append(grid)
        assert np.max(np.diff(grid[:,:,2],axis=0))<0,'Water climbs upwards'
        assert np.max(np.diff(grid[:,:,1],axis=0))<.01,'Water returns into cliff'
        entries=[]
        for column in range(len(columns)):
            points=grid[:,column]
            for a,b in zip(points,points[1:]):
                if a[2]>=-255>=b[2]:
                    p=a+(b-a)*((-255-a[2])/(b[2]-a[2]));break
            else:raise AssertionError('Water does not enter pool')
            q=(p[:2]-[430,3370])/[540,450]
            t=math.atan2(q[1],q[0]);radius=1+.045*math.sin(t*5)+.035*math.sin(t*9)
            entries.append(dict(point=p.tolist(),basinRadiusSquared=float(np.dot(q,q)/radius**2)))
        for row in grid[::4]:probes.extend(row[4:-4:4])
        widths=np.ptp(grid[:,:,0],axis=1)
        streams.append(dict(material=paint,rows=len(ordered),columns=len(columns),
                            widthRange=[float(np.min(widths)),float(np.max(widths))],
                            maximumBacktrack=float(np.max(np.diff(grid[:,:,1],axis=0))),entries=entries))
    seam_errors=[float(np.max(np.abs(a[:,-1]-b[:,0]))) for a,b in zip(grids,grids[1:])]
    assert max(seam_errors)<.002,'Adjacent water bands are disconnected'
    blocked=occlusion(np.array(probes),added)
    report=dict(scope='Offline OBJ geometry, new/refitted-rock principal-view rays, and all-column basin entry; no native shader/physics/performance proof.',
                triangleCount=sum(map(len,faces.values())),newOrRefittedRockTriangles=len(added),
                oldRockTrianglesRefitted=refitted_old_triangles,streams=streams,sharedEdgeMaximumErrors=seam_errors,
                overallWidthRange=[float(np.min(grids[-1][:,-1,0]-grids[0][:,0,0])),
                                   float(np.max(grids[-1][:,-1,0]-grids[0][:,0,0]))],
                ledgeRaySamples=len(probes),
                occludedByNewOrRefittedRock=blocked,
                candidateSha256=hashlib.sha256(file.read_bytes()).hexdigest())
    report['baselineSha256']=hashlib.sha256(args.baseline.read_bytes()).hexdigest()
    (args.candidate/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not blocked,f'{len(blocked)} water probes hidden by new/refitted rock'
    assert all(e['basinRadiusSquared']<1 for s in streams for e in s['entries']),'Water misses basin'
    print(json.dumps(dict(triangles=report['triangleCount'],newOrRefittedRockTriangles=len(added),
                          ledgeRaySamples=len(probes),occluded=0,
                          basinEntries=sum(len(s['entries']) for s in streams),
                          maximumBasinRadiusSquared=max(e['basinRadiusSquared'] for s in streams for e in s['entries']))))


if __name__=='__main__':main()
