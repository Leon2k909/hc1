"""Cast-iron street grates and real visual recesses for Lowtide.

Geometry is in plan inches. Pavement collision is intentionally retained: the
grate supports a player's feet. Only the rendered top surface has an opening.
The CLI stages exact local mesh replacements; it never writes live assets.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import uuid

import numpy as np
from PIL import Image
from scipy import ndimage

import map_kit as K

IRON = 'lt_grate_cast_iron'
WELL = 'lt_grate_well'
SOURCE = K.ROOT / 'Sources/Lowtide/drainage/cast-iron-source.png'
RESOURCE = 'materials/lowtide/drainage'
REVISION = 'recessed-cast-grates-v1'


def layout():
    for side in (-1, 1):
        for e in (390, 770, 1160, 1420, 1880, 2110):
            yield side * e, -1540, 23, 32
        for n in (-870, -505, -170, 180, 540, 920):
            yield side * 1030, n, 16, 26


def face(m, points, normal, paint=IRON):
    p = np.asarray(points, float)
    if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), normal) < 0:
        p = p[::-1]
    m.polygon(paint, list(p))


def contour(e, n, width, length, corner, z):
    x, y, r = width / 2, length / 2, corner
    return np.array([(e+a, n+b, z) for a,b in (
        (-x+r,-y),(x-r,-y),(x,-y+r),(x,y-r),
        (x-r,y),(-x+r,y),(-x,y-r),(-x,-y+r))])


def ring(m, e, n, width, length, thickness, top, bottom, bevel=.075):
    # One continuous casting, with a bevel on both lips and a recessed inside.
    loops = [contour(e,n,width,length,.28,bottom),
             contour(e,n,width,length,.28,top-bevel),
             contour(e,n,width-2*bevel,length-2*bevel,.24,top),
             contour(e,n,width-2*thickness+2*bevel,length-2*thickness+2*bevel,.2,top),
             contour(e,n,width-2*thickness,length-2*thickness,.16,top-bevel),
             contour(e,n,width-2*thickness,length-2*thickness,.16,bottom)]
    for j in range(len(loops)):
        a, b = loops[j], loops[(j+1) % len(loops)]
        for i in range(8):
            k = (i+1) % 8
            points = [a[i], a[k], b[k], b[i]]
            normal = np.cross(np.subtract(points[1],points[0]),np.subtract(points[2],points[0]))
            # This sequence walks outside -> top -> inside -> bottom.
            face(m, points, normal)


def cast_bar(m, e, n, length, width=.58, top=.07, bottom=-1.35):
    # Eight-sided rounded section catches a narrow rim highlight, never a
    # razor-sharp cube edge. Ends are buried in the removable grate's rim.
    h, r = width/2, .075
    section = [(-h+r,bottom),(h-r,bottom),(h,bottom+r),(h,top-r),
               (h-r,top),(-h+r,top),(-h,top-r),(-h,bottom+r)]
    loops = [np.array([(e+x,n+dy,z) for x,z in section]) for dy in (-length/2,length/2)]
    for i in range(8):
        k = (i+1) % 8
        normal = np.array([section[k][1]-section[i][1],0,section[i][0]-section[k][0]])
        face(m,[loops[0][i],loops[1][i],loops[1][k],loops[0][k]],normal)
    face(m, loops[0], (0,-1,0))
    face(m, loops[1], (0,1,0))


def grate(m, e, n, width=23, length=32):
    ring(m,e,n,width+1.2,length+1.6,.80,.19,-1.8)
    # A real narrow clearance separates the lift-out insert from its frame.
    iw, il = width-.70, length-.30
    ring(m,e,n,iw,il,.74,.07,-1.45)
    usable = iw - 2*.74
    count = max(5, round(usable/2.05))
    for i in range(count):
        x = -usable/2 + (i+.5)*usable/count
        cast_bar(m,e+x,n,il-1.15)
    # Two transverse supports are below the top of the slots, visible in
    # oblique views, rather than a second coplanar grille.
    for y in (-il*.22,il*.22):
        m.box((e-usable/2,n+y-.30,-1.65),(e+usable/2,n+y+.30,-.77),IRON)
    # The well extends ten inches below the paving. No cap crosses its mouth.
    halfw, halfl = width/2+.1, length/2+.2
    m.box((e-halfw-.15,n-halfl-.15,-10.5),(e+halfw+.15,n+halfl+.15,-10),WELL)
    for x in (-halfw, halfw):
        m.box((e+x-.12,n-halfl,-10),(e+x+.12,n+halfl,-.55),WELL)
    for y in (-halfl, halfl):
        m.box((e-halfw,n+y-.12,-10),(e+halfw,n+y+.12,-.55),WELL)


def legacy_grate(m,e,n,width=23,length=32):
    """Exact old component, used only to scope the one-time live replacement."""
    m.box((e-width/2,n-length/2,.02),(e+width/2,n+length/2,.10),'lt_drain_iron')
    for x in (-width/2,width/2):
        m.box((e+x-.6,n-length/2-.8,.10),(e+x+.6,n+length/2+.8,.45),'lt_drain_edge')
    for y in np.arange(-length/2,length/2+1,3):
        m.box((e-width/2,n+y-.45,.12),(e+width/2,n+y+.45,.40),'lt_drain_edge')


def configure(m):
    for paint in (IRON,WELL):
        if paint in m.polygons:
            m.material_overrides[paint] = f'{RESOURCE}/{paint}.vmat'
            m.tile_overrides[paint] = 12.


def halfplane(poly, axis, bound, less):
    """Clip a convex polygon with all per-vertex attributes interpolated."""
    result = []
    for a,b in zip(poly,np.roll(poly,-1,axis=0)):
        da,db = a[axis]-bound,b[axis]-bound
        ina,inb = (da<=1e-9,db<=1e-9) if less else (da>=-1e-9,db>=-1e-9)
        if ina: result.append(a)
        if ina != inb:
            result.append(a+(b-a)*(da/(da-db)))
    clean = []
    for p in result:
        if not clean or np.linalg.norm(p[:3]-clean[-1][:3])>1e-8: clean.append(p)
    if len(clean)>1 and np.linalg.norm(clean[0][:3]-clean[-1][:3])<1e-8: clean.pop()
    return np.asarray(clean)


def subtract(poly, rect):
    e,n,w,l = rect
    bounds = [(0,e-w/2-.1,False),(0,e+w/2+.1,True),
              (1,n-l/2-.2,False),(1,n+l/2+.2,True)]
    inside, outside = poly, []
    for axis,bound,less in bounds:
        if len(inside)<3: break
        part = halfplane(inside,axis,bound,not less)
        if len(part)>=3 and area(part)>1e-8: outside.append(part)
        inside = halfplane(inside,axis,bound,less)
    return outside, area(inside) if len(inside)>=3 else 0.


def area(p):
    a = p[1:-1,:2]-p[0,:2]
    b = p[2:,:2]-p[0,:2]
    return abs(np.sum(a[:,0]*b[:,1]-a[:,1]*b[:,0]))/2


def cut_polygon(poly, rects):
    parts = [poly]
    removed = 0.
    for r in rects:
        e,n,w,l = r
        lo,hi = poly[:,:2].min(axis=0),poly[:,:2].max(axis=0)
        if hi[0]<e-w/2-.1 or lo[0]>e+w/2+.1 or hi[1]<n-l/2-.2 or lo[1]>n+l/2+.2:
            continue
        next_parts = []
        for part in parts:
            pieces,loss = subtract(part,r)
            next_parts.extend(pieces)
            removed += loss
        parts = next_parts
    return parts,removed


def cut_model(m):
    """Canonical generator hook; keep boxes/hulls and non-paving faces intact."""
    paint = 'setts'
    faces = m.polygons.get(paint,[])
    old_uv = {i:m.polygon_uvs.get((paint,i)) for i in range(len(faces))}
    old_normals = {i:m.polygon_normals.get((paint,i)) for i in range(len(faces))}
    m.polygons[paint] = []
    for mapping in (m.polygon_uvs,m.polygon_normals):
        for key in list(mapping):
            if key[0]==paint: del mapping[key]
    for i,(points,normal) in enumerate(faces):
        points = np.asarray(points)
        uv = old_uv[i]
        if np.max(np.abs(points[:,2]))<.001 and normal[2]>.99:
            packed = np.concatenate([points,np.asarray(uv)],axis=1) if uv is not None else points
            pieces,_ = cut_polygon(packed,list(layout()))
            for p in pieces: m.polygon(paint,p[:,:3],normal,uv=p[:,3:5] if uv is not None else None)
        else:
            m.polygon(paint,points,normal,uv=uv,normals=old_normals[i])


def cut_obj(text):
    """Preserve original OBJ records and append only the cut paving triangles."""
    vs,ts,ns,keep,addition = [],[],[],[],[]
    paint = None
    lost,changed = 0.,0
    for line in text.splitlines():
        s = line.split()
        if s and s[0]=='v': vs.append(tuple(map(float,s[1:])))
        elif s and s[0]=='vt': ts.append(tuple(map(float,s[1:])))
        elif s and s[0]=='vn': ns.append(tuple(map(float,s[1:])))
        elif s and s[0]=='usemtl': paint=s[1]
        elif s and s[0]=='f' and paint=='setts':
            refs = [tuple(int(v)-1 for v in item.split('/')) for item in s[1:]]
            p = np.asarray([(-vs[v][0],vs[v][2],vs[v][1],*ts[t],*ns[n]) for v,t,n in refs])
            if np.max(np.abs(p[:,2]))<.001 and np.mean(p[:,6])>.99:
                parts,loss = cut_polygon(p,list(layout()))
                if loss>1e-6:
                    addition.extend(parts)
                    lost += loss
                    changed += 1
                    continue
        keep.append(line)
    assert changed>0, 'No pavement triangles intersect the saved grate positions'
    vbase,tbase,nbase = len(vs),len(ts),len(ns)
    keep.extend(['# '+REVISION,'usemtl setts'])
    added_triangles = 0
    for p in addition:
        for x in p:
            keep.extend([f'v {-x[0]:.3f} {x[2]:.3f} {x[1]:.3f}',f'vt {x[3]:.5f} {x[4]:.5f}',f'vn {x[5]:.3f} {x[6]:.3f} {x[7]:.3f}'])
        for i in range(1,len(p)-1):
            ids = (0,i,i+1)
            cross = np.cross(p[i,:3]-p[0,:3],p[i+1,:3]-p[0,:3])
            if np.linalg.norm(cross)<1e-7: continue
            keep.append('f '+' '.join(f'{vbase+j+1}/{tbase+j+1}/{nbase+j+1}' for j in ids))
            added_triangles += 1
        vbase += len(p); tbase += len(p); nbase += len(p)
    expected = sum((w+.2)*(l+.4) for e,n,w,l in layout())/2
    assert abs(lost-expected)<.01, (lost,expected)
    return '\n'.join(keep)+'\n',dict(changed_faces=changed,added_faces=added_triangles,opening_area=lost)


def write_materials(asset_root=None):
    root = Path(asset_root) if asset_root is not None else K.ASSETS
    out = root/RESOURCE
    out.mkdir(parents=True,exist_ok=True)
    # Preserve the generated artwork: only resize to the engine's mip dimensions.
    rgb = Image.open(SOURCE).convert('RGB').resize((2048,2048),Image.Resampling.LANCZOS)
    rgb.save(out/'cast_iron_color.png')
    a = np.asarray(rgb,dtype=np.float32)/255
    lum = a@np.array([.2126,.7152,.0722])
    grain = ndimage.gaussian_filter(lum,1.1,mode='wrap')-ndimage.gaussian_filter(lum,10,mode='wrap')
    dx = (np.roll(grain,-1,1)-np.roll(grain,1,1))*.65
    dy = (np.roll(grain,-1,0)-np.roll(grain,1,0))*.65
    normals = np.stack([-dx,dy,np.ones_like(dx)],axis=-1)
    normals /= np.linalg.norm(normals,axis=-1,keepdims=True)
    Image.fromarray(np.rint((normals*.5+.5)*255).clip(0,255).astype('uint8')).save(out/'cast_iron_normal.png')
    rough = np.clip(.68-grain*.65,.56,.79)
    Image.fromarray(np.rint(rough*255).astype('uint8')).save(out/'cast_iron_rough.png')
    for paint,tint,metal in ((IRON,1.,.65),(WELL,.15,.05)):
        (out/f'{paint}.vmat').write_text(f'''// {REVISION}: generated cast-iron surface, 12-inch physical tile.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "{RESOURCE}/cast_iron_color.png"
    TextureNormal "{RESOURCE}/cast_iron_normal.png"
    TextureRoughness "{RESOURCE}/cast_iron_rough.png"
    g_vColorTint "[{tint} {tint} {tint} 1]"
    g_flMetalness "{metal}"
}}
''',encoding='utf-8')
    for p in out.iterdir():
        if p.suffix not in ('.png','.vmat'): continue
        meta = p.with_name(p.name+'.meta')
        if not meta.exists():
            meta.write_text(json.dumps({'guid':str(uuid.uuid5(uuid.NAMESPACE_URL,p.relative_to(root).as_posix()))},indent=2)+'\n')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).is_file() else None


def stage(out):
    import lowtide_map as L
    import lowtide_window_construction as W
    out = Path(out).resolve()
    assert out.is_relative_to((K.ROOT/'output/lowtide').resolve())
    assets = out/'stage/Assets'
    models = assets/'models/maps/lowtide'
    models.mkdir(parents=True,exist_ok=True)
    old,new = K.Model(),K.Model()
    for record in layout():
        legacy_grate(old,*record)
        grate(new,*record)
    L.configure(old); L.configure(new); configure(new)
    W.validate_model(new)
    for name,m in (('old',old),('new',new)):
        K.write_obj(out/f'grates-{name}.obj',m,'lowtide_finish')
    source = K.ASSETS/'models/maps/lowtide/lowtide_finish.obj'
    before = source.read_text()
    result,removed = W.replace_faces(before,(out/'grates-old.obj').read_text(),(out/'grates-new.obj').read_text())
    assert removed==old.triangle_count()
    expected = W.face_keys(before,attributes=True)-W.face_keys((out/'grates-old.obj').read_text(),attributes=True)+W.face_keys((out/'grates-new.obj').read_text(),attributes=True)
    assert W.face_keys(result,attributes=True)==expected
    (models/source.name).write_text(result,encoding='utf-8')
    mtl = source.with_suffix('.mtl').read_text()
    for paint in (IRON,WELL): mtl += f'\nnewmtl {paint}\nKd 1 1 1\nd 1\n'
    (models/source.with_suffix('.mtl').name).write_text(mtl,encoding='utf-8')
    vmdl = source.with_suffix('.vmdl').read_text()
    marker = 'remaps =\n\t\t\t\t\t\t['
    assert vmdl.count(marker)==1
    remaps = ''.join(f'\n\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{RESOURCE}/{p}.vmat" }},' for p in (IRON,WELL))
    (models/source.with_suffix('.vmdl').name).write_text(vmdl.replace(marker,marker+remaps),encoding='utf-8')
    holes = {}
    for name in ('lowtide_east','lowtide_west'):
        source = K.ASSETS/f'models/maps/lowtide/{name}.obj'
        result,holes[name] = cut_obj(source.read_text())
        (models/source.name).write_text(result,encoding='utf-8')
    write_materials(assets)
    staged = {p.relative_to(out/'stage').as_posix():sha(p) for p in (out/'stage').rglob('*') if p.is_file()}
    before_hashes = {p:sha(K.ROOT/p) for p in staged}
    for relative,value in before_hashes.items():
        if value is None: continue
        target = out/'before'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists(): assert sha(target)==value, 'Live assets changed since staging'
        else: shutil.copy2(K.ROOT/relative,target)
    manifest = dict(revision=REVISION,project_root=str(K.ROOT),grates=24,
        old_triangles=old.triangle_count(),new_triangles=new.triangle_count(),
        delta_triangles=new.triangle_count()-old.triangle_count(),
        unrelated_finish_triangles=sum(W.face_keys(before).values())-removed,
        pavement=holes,collision_changed=False,new_material_slots=2,
        live_before=before_hashes,staged_files=staged,
        source_image=str(SOURCE.relative_to(K.ROOT)),source_image_sha256=sha(SOURCE))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in ('live_before','staged_files')},indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    stage(parser.parse_args().output)
