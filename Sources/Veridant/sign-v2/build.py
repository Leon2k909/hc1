"""Scoped reception sign rebuild; retain unrelated OBJ records and all physics."""
from pathlib import Path
import sys, json, re, hashlib
import numpy as np
import cv2
from PIL import Image
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import veridant_map as V
import veridant_parts as P
OUT=ROOT/'output/veridant/sign-v2'
RESOURCE='models/maps/veridant/sign-v2'

def polys(g):
    return [g] if g.geom_type=='Polygon' else [p for p in g.geoms if p.geom_type=='Polygon']

def glyph(name, centre, width, height):
    atlas=Image.open(ROOT/'Assets/materials/veridant/vr_letters_trans.png')
    x,y,w,h=V.VM.LETTERS[name]
    mask=np.array(atlas.crop((x,y,x+w,y+h)))
    contours,hierarchy=cv2.findContours((mask>127).astype('uint8'),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    def coords(c):
        q=cv2.approxPolyDP(c,.65,True)[:,0,:]
        return [(centre[0]+(a/w-.5)*width,centre[1]+(.5-b/h)*height) for a,b in q]
    shapes=[]
    for i,c in enumerate(contours):
        if hierarchy[0,i,3]!=-1 or cv2.contourArea(c)<4: continue
        holes=[]; child=hierarchy[0,i,2]
        while child!=-1:
            holes.append(coords(contours[child])); child=hierarchy[0,child,0]
        shapes.append(Polygon(coords(c),holes).buffer(0))
    return unary_union(shapes)

def face(m,paint,points,normal):
    pts=[]
    for p in points:
        if not pts or np.linalg.norm(np.array(p)-pts[-1])>1e-7: pts.append(np.array(p,float))
    if len(pts)>2 and np.linalg.norm(pts[0]-pts[-1])<1e-7: pts.pop()
    if len(pts)<3: return
    if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0: pts.reverse()
    m.polygon(paint,pts,normal=np.array(normal,float))

def sheet(m,shape,e,paint):
    for poly in polys(shape):
        for tri in constrained_delaunay_triangles(poly).geoms:
            q=list(tri.exterior.coords)[:3]
            face(m,paint,[(e,n,z) for n,z in q],(1,0,0))

def chamfered_block(m,e0,e1,n0,n1,z0,z1,b,paint,omit_front=False):
    # Front and back inset rectangles joined to an eight-sided belt.
    belt=[(e0+b,n0),(e1-b,n0),(e1,n0+b),(e1,n1-b),(e1-b,n1),(e0+b,n1),(e0,n1-b),(e0,n0+b)]
    for lo,hi in ((z0+b,z1-b),):
        for i,a in enumerate(belt):
            c=belt[(i+1)%8]
            if omit_front and a[0]==e1 and c[0]==e1: continue
            norm=np.array((c[1]-a[1],a[0]-c[0],0.)); norm/=np.linalg.norm(norm)
            face(m,paint,[(a[0],a[1],lo),(c[0],c[1],lo),(c[0],c[1],hi),(a[0],a[1],hi)],norm)
    for z,innerz,sg in ((z0,z0+b,-1),(z1,z1-b,1)):
        inner=[(e0+b,n0+b),(e1-b,n0+b),(e1-b,n1-b),(e0+b,n1-b)]
        face(m,paint,[(e,n,z) for e,n in inner],(0,0,sg))
        # Each octagonal belt edge projects to the inset top/bottom rectangle.
        for i,a in enumerate(belt):
            c=belt[(i+1)%8]
            ai=(min(max(a[0],e0+b),e1-b),min(max(a[1],n0+b),n1-b))
            ci=(min(max(c[0],e0+b),e1-b),min(max(c[1],n0+b),n1-b))
            pts=[(a[0],a[1],innerz),(c[0],c[1],innerz),(ci[0],ci[1],z),(ai[0],ai[1],z)]
            if np.linalg.norm(np.cross(np.subtract(pts[1],pts[0]),np.subtract(pts[2],pts[0])))<1e-8: continue
            normal=np.cross(np.subtract(pts[1],pts[0]),np.subtract(pts[2],pts[0])); normal[2]=abs(normal[2])*sg
            face(m,paint,pts,normal/np.linalg.norm(normal))

def build_sign():
    m=K.Model(); m.uv_source_name='veridant_dress'
    chamfered_block(m,110,140,96,196,4,166,.65,'vr_stone',True)
    chamfered_block(m,109,141,95,197,166,170,.35,'vr_stone_dark')
    chamfered_block(m,111,139,97,195,0,4,.25,'vr_stone_dark')
    width=100.; h=170.
    cuts=unary_union([
        glyph('logo',(146,h*.66),width*.34,width*.34),
        glyph('veridant',(146,h*.48),width*.82,width*.82/V.VM.aspect(V.VM.LETTERS,'veridant')),
        glyph('resort',(146,h*.405),width*.42,width*.42/V.VM.aspect(V.VM.LETTERS,'resort'))])
    front=box(96.65,4.65,195.35,165.35)
    sheet(m,front.difference(cuts),140,'vr_stone')
    sheet(m,cuts,139.5,'vr_dark')
    for poly in polys(cuts):
        for ring in [poly.exterior,*poly.interiors]:
            q=list(ring.coords)
            for a,b in zip(q,q[1:]):
                mid=np.array(((a[0]+b[0])/2,(a[1]+b[1])/2))
                d=np.array((b[1]-a[1],a[0]-b[0])); d/=np.linalg.norm(d)
                from shapely.geometry import Point
                if not cuts.contains(Point(*(mid+d*.001))): d=-d
                face(m,'vr_stone_dark',[(140,*a),(140,*b),(139.5,*b),(139.5,*a)],(0,d[0],d[1]))
    V.configure(m)
    return m

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/'Assets/models/maps/veridant/chair-v2/dress-base.obj'
    before=OUT/'before'; before.mkdir(exist_ok=True)
    for rel in ('models/maps/veridant/chair-v2/dress-base.obj','models/maps/veridant/veridant_dress.vmdl'):
        dst=before/Path(rel).name
        if not dst.exists(): dst.write_bytes((ROOT/'Assets'/rel).read_bytes())
    orig=Path(__file__).with_name('original-sign.obj')
    def keys(lines):
        vs=[]; mat=''; result=[]
        for line in lines:
            if line.startswith('v '): vs.append(tuple(round(float(x),3) for x in line.split()[1:]))
            elif line.startswith('usemtl '): mat=line.split()[1]
            elif line.startswith('f '):
                pts=tuple(sorted(vs[int(t.split('/')[0])-1] for t in line.split()[1:]))
                result.append((mat,pts))
        return result
    targets=set(keys(orig.read_text().splitlines()))
    lines=(before/'dress-base.obj').read_text().splitlines(keepends=True)
    allkeys=iter(keys(lines)); kept=[]; removed=[]
    for line in lines:
        if line.startswith('f '):
            key=next(allkeys)
            if key in targets: removed.append(line); continue
        kept.append(line)
    assert len(removed)==len(targets),(len(removed),len(targets))
    stage=OUT/'stage'; target=stage/'models/maps/veridant/sign-v2'; target.mkdir(parents=True,exist_ok=True)
    (target/'dress-without-sign.obj').write_text(''.join(kept))
    mtl=re.search(r'^mtllib (.+)$',''.join(kept),re.M).group(1).strip()
    (target/mtl).write_bytes((source.parent/mtl).read_bytes())
    replacement=build_sign(); K.write_obj(target/'sign.obj',replacement,'veridant_dress')
    vmdl=(before/'veridant_dress.vmdl').read_text()
    vmdl=vmdl.replace('models/maps/veridant/chair-v2/dress-base.obj',RESOURCE+'/dress-without-sign.obj',1)
    match=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',vmdl,re.S)
    node=match.group().replace('name = "veridant_dress"','name = "reception_sign_v2"').replace(RESOURCE+'/dress-without-sign.obj',RESOURCE+'/sign.obj')
    vmdl=vmdl[:match.end()]+ '\n'+node+vmdl[match.end():]
    parent=stage/'models/maps/veridant/veridant_dress.vmdl'; parent.parent.mkdir(parents=True,exist_ok=True); parent.write_text(vmdl)
    report={'removed_triangles':len(removed),'new_triangles':replacement.triangle_count(),'preserved_records':len(kept),'recess_depth_inches':.5,'source_sha256':hashlib.sha256((before/'dress-base.obj').read_bytes()).hexdigest(),'all_original_indices_preserved':True}
    # Compare the full physics suffix, including every existing collider import.
    old=(before/'veridant_dress.vmdl').read_text(); report['physics_unchanged']=vmdl[vmdl.index('_class = "PhysicsShapeList"'):]==old[old.index('_class = "PhysicsShapeList"'):]
    assert report['physics_unchanged']
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))

if __name__=='__main__': main()
