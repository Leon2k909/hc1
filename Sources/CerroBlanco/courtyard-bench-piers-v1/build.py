"""One review bench: reuse the existing teak seat with two travertine piers."""
from pathlib import Path
import sys,json,numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import cerroblanco_courtyard_bench as C
import riverdale_parts as P
original_stone=C.stone;original_build=C.build;original_screw=C.B.screw
OUT=ROOT/'output/cerroblanco/courtyard-bench-piers-v1'
RESOURCE='models/maps/cerroblanco/courtyard-bench-piers-v1'

def piers(m,centre,size,radius):
    if size==(89.2,19.2,.7):
        for x in (-29,29):original_stone(m,(x,0,.35),(10.4,17.6,.7),.12)
    elif size==(90,20,16.3):
        for x in (-29,29):original_stone(m,(x,0,8.85),(12,19.2,16.3),.35)
        # Two longitudinal steel tubes support the long seat boards between piers.
        for y in (-5.5,5.5):
            P.bevel_box(m,(0,y,16.35),((1,0,0),(0,1,0),(0,0,1)),(70,1.5,1.3),'vr_bench_recess',bevel=.10)
    else:raise ValueError(('Unexpected body',centre,size))

def build():
    def screw(m,x,y,z):
        original_screw(m,x,y,z)
        # Triangulate the concave recess around its centre, so no fan triangle
        # folds outside the six-lobed outline.
        points,normal=m.polygons['vr_bench_recess'].pop()
        centre=np.mean(points,axis=0)
        for a,b in zip(points,points[1:]+points[:1]):
            P.card(m,'vr_bench_recess',[centre,a,b],normal)
    C.stone=piers;C.B.screw=screw
    try:return original_build()
    finally:C.stone=original_stone;C.B.screw=original_screw

if __name__=='__main__':
    C.OUT=OUT;C.RESOURCE=RESOURCE;C.build=build;C.main()
    m=build();assert len(m.boxes)==0 and len(m.hulls)==0
    # No centre stone pier: retain a real opening beneath the seat.
    for pts,n in m.polygons['cb_honed']:
        assert all(abs(p[0]+250)>=22.9 for p in pts)
    verts=[];normals=[];tris=0;issues=[];material=''
    path=OUT/'bench-only.obj'
    for line in path.read_text().splitlines():
        if line.startswith('v '):verts.append(np.array([float(x) for x in line.split()[1:]]))
        elif line.startswith('vn '):normals.append(np.array([float(x) for x in line.split()[1:]]))
        elif line.startswith('usemtl '):material=line.split()[1]
        elif line.startswith('f '):
            ids=[x.split('/') for x in line.split()[1:]];a,b,c=[verts[int(x[0])-1] for x in ids]
            cross=np.cross(b-a,c-a);assert np.linalg.norm(cross)>1e-9
            score=np.dot(cross,sum(normals[int(i[2])-1] for i in ids))/np.linalg.norm(cross)
            if score<0:issues.append((material,score,float(np.linalg.norm(cross)/2)))
            tris+=1
    assert np.isfinite(verts).all() and np.isfinite(normals).all()
    assert not issues,issues[:8]
    report={'triangles':tris,'finite_non_degenerate_faces':True,'outward_winding':True,'open_space_between_piers':True,'no_added_collision':True}
    (OUT/'shape-checks.json').write_text(json.dumps(report,indent=2));print(report)
