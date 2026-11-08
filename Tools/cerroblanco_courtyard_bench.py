"""Stage one courtyard bench rebuild, preserving all other packed dressing faces.

Uses the established Veridant bench's shaped teak, end grain and fasteners.
The museum's honed-stone material and original solid collision remain in use.
No live assets or scenes are written by this script.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import map_kit as K
import veridant_bench as B
from cerroblanco_bollards_upgrade import split_obj, remap_faces

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/cerroblanco/courtyard-bench-v1'
RESOURCE='models/maps/cerroblanco/courtyard-bench-v1'
SOURCE=ROOT/'Assets/models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj'


def stone(m,centre,size,radius):
    """A closed chamfered block: six faces, twelve arrises and eight corners."""
    c=np.asarray(centre,float);half=np.asarray(size,float)/2
    def face(pts):
        normal=np.cross(pts[1]-pts[0],pts[2]-pts[0])
        if np.dot(normal,np.mean(pts,axis=0)-c)<0: pts.reverse()
        m.polygon('cb_honed',pts)
    for axis in range(3):
        a,b=[i for i in range(3) if i!=axis]
        for side in (-1,1):
            pts=[]
            for u,v in ((-1,-1),(1,-1),(1,1),(-1,1)):
                p=c.copy();p[axis]+=side*half[axis]
                p[a]+=u*(half[a]-radius);p[b]+=v*(half[b]-radius);pts.append(p)
            face(pts)
    for axis in range(3):
        a,b=[i for i in range(3) if i!=axis]
        for sa in (-1,1):
            for sb in (-1,1):
                pts=[]
                for end,inset in ((-1,a),(1,a),(1,b),(-1,b)):
                    p=c.copy();p[axis]+=end*(half[axis]-radius)
                    p[a]+=sa*half[a];p[b]+=sb*half[b]
                    p[inset]-=radius*(sa if inset==a else sb);pts.append(p)
                face(pts)
    for sx in (-1,1):
        for sy in (-1,1):
            for sz in (-1,1):
                signs=np.array((sx,sy,sz));corner=c+half*signs
                face([corner-np.eye(3)[a]*signs[a]*radius for a in range(3)])


def build():
    m=K.Model()
    # Solid stone body, with eased arrises and a recessed foot/shadow joint.
    stone(m,(0,0,.35),(89.2,19.2,.7),.12)
    stone(m,(0,0,8.85),(90,20,16.3),.22)
    # Reproject the stone at the museum's existing scale rather than the helper's
    # concrete UV scale. No tiled seam is introduced across a bevel.
    for i,(pts,normal) in enumerate(m.polygons['cb_honed']):
        m.polygon_uvs['cb_honed',i]=[K.face_uv(K.to_world(p+np.array((-250,-800,0))),
            K.to_world(normal),'cb_honed',K.uv_offset('cerroblanco_dressing'),120) for p in pts]
    for x in (-31,31):
        B.rounded_member(m,(x,0,17.10),(1.6,17.4,.20),.07,'vr_bench_recess')
    for i,y in enumerate((-7.2,-3.6,0,3.6,7.2)):
        paint=('vr_bench_teak','vr_bench_teak_light','vr_bench_teak',
               'vr_bench_teak_dark','vr_bench_teak')[i]
        B.rounded_member(m,(0,y,17.9),(82,3.2,1.4),.17,paint,
                         phase=i*1.7,wood=True,wood_region=i%4)
        for x in (-31,31): B.screw(m,x,y,18.60)
    # Translate to the one existing bench's world placement.
    for paint,faces in m.polygons.items():
        for i,(pts,normal) in enumerate(faces):
            faces[i]=([p+np.array((-250,-800,0)) for p in pts],normal)
    m.material_overrides.update(B.MATERIALS)
    m.material_overrides['cb_honed']='materials/cerroblanco/quality-v1/cb_honed.vmat'
    m.tile_overrides.update({paint:120 for paint in m.polygons})
    return m


def main():
    dest=OUT/'stage'/RESOURCE
    dest.mkdir(parents=True,exist_ok=True)
    source=SOURCE.read_bytes()
    lines,vertices,uvs,normals=split_obj(source.decode('utf-8'))
    kept=[];removed=[];material=''
    for line in lines:
        if line.startswith('usemtl '): material=line.split()[1]
        if line.startswith('f ') and material in ('cb_honed','cb_teak'):
            points=[vertices[int(t.split('/')[0])-1] for t in line.split()[1:]]
            if all(205-.001<=x<=295+.001 and -.001<=z<=18.601
                   and -810.001<=n<=-789.999 for x,z,n in points):
                removed.append(line);continue
        kept.append(line)
    assert len(removed)==70, f'Unexpected source geometry: {len(removed)} faces'
    fresh=OUT/'bench-only.obj'
    added=K.write_obj(fresh,build(),'courtyard_bench')
    new,nv,nt,nn=split_obj(fresh.read_text())
    merged=[];inserted=set()
    groups=[('vt ','v',[s for s in new if s.startswith('v ')]),
            ('vn ','vt',nt),('usemtl ','vn',nn)]
    for line in kept:
        for prefix,key,values in groups:
            if line.startswith(prefix) and key not in inserted:
                merged.extend(values);inserted.add(key)
        merged.append(line)
    assert inserted=={'v','vt','vn'}
    merged.extend(remap_faces(new,len(vertices),len(uvs),len(normals)))
    text='\n'.join(merged)+'\n'
    (dest/'courtyard_dressing.obj').write_text(text)
    template=SOURCE.with_suffix('.vmdl').read_text()
    template=template.replace('models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.obj',
                              RESOURCE+'/courtyard_dressing.obj')
    extra='\n'.join('{ from = "'+k+'.vmat" to = "'+v+'" },' for k,v in B.MATERIALS.items())
    marker='{ from = "soil.vmat" to = "materials/buildings/soil.vmat" }'
    assert marker in template
    template=template.replace(marker,marker+',\n'+extra)
    (dest/'courtyard_dressing.vmdl').write_text(template)
    # MTL is a source dependency; ModelDoc remaps provide the real materials.
    original_mtl=SOURCE.with_suffix('.mtl').read_text()
    original_mtl+='\n'+fresh.with_suffix('.mtl').read_text()
    (dest/'courtyard_dressing.mtl').write_text(original_mtl)
    (dest/'courtyard_dressing.obj').write_text(text.replace('mtllib cerroblanco_dressing_v2.mtl','mtllib courtyard_dressing.mtl'))
    report={'source_sha256':hashlib.sha256(source).hexdigest(),'removed_triangles':70,
            'added_triangles':added,'other_faces_preserved':sum(s.startswith('f ') for s in kept),
            'placement_plan':[-250,-800,0],'collision':'original solid stone collider retained',
            'stage_only':True}
    (OUT/'geometry-checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
