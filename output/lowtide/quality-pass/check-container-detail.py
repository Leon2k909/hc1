"""Check saved source scope and rays through the actual exported casting apertures."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import lowtide_container as C
import map_kit as K
import railhead_props as P
OUT=Path(__file__).resolve().parent/'container-detail'
manifest=json.loads((OUT/'manifest.json').read_text())
staged='--staged' in sys.argv
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for relative,expected in manifest['protected'].items():
    assert digest(ROOT/relative)==expected,relative
for relative,expected in manifest['changes'].items():
    assert digest((OUT/'stage'/relative) if staged else (ROOT/'Assets'/relative))==expected['after'],relative

def triangles(path):
    vertices=[]
    triangles=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            # map_kit exports world (x,y,z) as OBJ (y,z,x).
            y,z,x=map(float,line.split()[1:])
            vertices.append((x,y,z))
        elif line.startswith('f '): triangles.append([vertices[int(v.split('/')[0])-1] for v in line.split()[1:]])
    return np.asarray(triangles)

ray_count=0
for name,records in C.layouts().items():
    tris=triangles(OUT/(name+'-new.obj'))
    original=triangles(OUT/(name+'-old.obj'))
    assert np.allclose(tris.min(axis=(0,1)),original.min(axis=(0,1)))
    assert np.allclose(tris.max(axis=(0,1)),original.max(axis=(0,1)))
    edge1,edge2=tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]
    for args,kwargs in records:
        e,n,z,size,axis,paint=args
        frame=P.Frame((e,n,z),(1,0) if axis=='e' else (0,1))
        half_length=P.CONTAINER_SIZES[size]/2
        container_centre=K.to_world((e,n,z+51))
        for sx in (-1,1):
            for sy in (-1,1):
                for z0,z1 in ((-.05,4.6),(97.4,102.05)):
                    p=K.to_world(frame.p(sx*48.05,sy*(half_length+.05),z0))
                    q=K.to_world(frame.p(sx*41,sy*(half_length-6.4),z1))
                    centre=(p+q)/2
                    half=abs(p-q)/2
                    for axis in range(3):
                        sign=1 if centre[axis]>container_centre[axis] else -1
                        origin=centre.copy()
                        origin[axis]+=sign*(half[axis]+.05)
                        direction=-np.eye(3)[axis]*sign
                        h=np.cross(direction,edge2)
                        determinant=np.einsum('ij,ij->i',edge1,h)
                        valid=abs(determinant)>1e-8
                        inv=np.divide(1,determinant,out=np.zeros_like(determinant),where=valid)
                        offset=origin-tris[:,0]
                        u=np.einsum('ij,ij->i',offset,h)*inv
                        cross=np.cross(offset,edge1)
                        v=(cross@direction)*inv
                        distance=np.einsum('ij,ij->i',edge2,cross)*inv
                        hit=valid&(u>=-1e-7)&(v>=-1e-7)&(u+v<=1.0000001)&(distance>1e-6)
                        assert hit.any(), (name, centre.tolist(), axis, 'ray missed')
                        nearest=distance[hit].min()
                        expected=2*half[axis]-.65+.05
                        assert abs(nearest-expected)<.001,(name,centre,axis,nearest,expected)
                        ray_count+=1

native=json.loads((OUT/'native-verify.json').read_text()) if not staged else None
if native:
    assert native['sourceHashes']=={p:c['after'] for p,c in manifest['changes'].items()}
    assert not native['modelErrors'] and not native['materialErrors']
    assert not native['HasUnsavedChanges'] and not native['IsPlaying']
    assert len(native['captures'])==4
    for name in native['captures']:
        assert (OUT.parent/name).stat().st_size>100000
report={'status':'staged data verified' if staged else 'installed and verified','protected_files':len(manifest['protected']),
        'open_casting_aperture_rays':ray_count,'bounds_unchanged':True,
        'visual_triangles_added':sum(m['added']-m['removed'] for m in manifest['models'].values()),
        'outside_container_faces_preserved_per_half':322708,
        'native_report':'native-verify.json' if native else None,'captures_reviewed':native['captures'] if native else [],
        'limits':'Geometry pass only. Broad surface finish and the overall AAA goal remain open. No controlled gameplay performance comparison was run.'}
(OUT/('staged-data-checks.json' if staged else 'verification.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
