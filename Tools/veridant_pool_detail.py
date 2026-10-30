"""The courtyard's shallow reflecting basin, jointed coping and fractured rocks.

Uses the existing pool footprint and collision. New render geometry stays inside
the old rock hulls; source scans are the already installed CC0 Spillway rock set.
"""
import math
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull
from scipy.special import logsumexp

import map_kit as K
import veridant_parts as P
from riverdale_parts import UP, card, v

RESOURCE = 'materials/veridant/pool-v2'
MATERIALS = {f'vr_pool_{name}': f'{RESOURCE}/{name}.vmat' for name in
             ('coping', 'coping_light', 'coping_dark', 'joint', 'liner', 'rock', 'rock_damp', 'rock_wet')}


def _surface(colour, normal, rough, tint=(1, 1, 1), exponent=1):
    return ('// Tools/veridant_pool_detail.py\n"Layer0"\n{\n'
            '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
            f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n'
            f'    TextureRoughness "{rough}"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n'
            f'    g_flRoughnessScaleFactor "{exponent}"\n'
            '    g_flMetalness "0"\n    g_flModelTintAmount "1"\n}\n')


def write_materials(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    scan = 'materials/spillway/scans/'
    rock = (scan+'seaside_rock_diff_2k.jpg', scan+'seaside_rock_nor_dx_2k.jpg', scan+'seaside_rock_rough_2k.jpg')
    for name, tint, exponent in (('rock', (1.30, 1.27, 1.18), .85),
                                 ('rock_damp', (1.10, 1.13, 1.07), 1.7),
                                 ('rock_wet', (.89, .98, .93), 2.6)):
        (directory/f'{name}.vmat').write_text(_surface(*rock, tint, exponent))
    base = ('materials/veridant/vr_rock_color.jpg', 'materials/veridant/vr_rock_normal.jpg',
            'materials/veridant/vr_rock_rough.png')
    for name, tint in (('coping', (.82, .81, .77)), ('coping_light', (.88, .86, .81)),
                       ('coping_dark', (.74, .75, .73))):
        (directory/f'{name}.vmat').write_text(_surface(*base, tint, 1.25))
    (directory/'liner.vmat').write_text(_surface(*base, (.82, 1.02, .97), 1.6))
    (directory/'joint.vmat').write_text(_surface('[0.13 0.145 0.14 0]',
        'materials/default/default_normal.tga', '[0.84 0.84 0.84 0]'))


def water_material():
    return ('// Tools/veridant_pool_detail.py: clear shallow water, pool-v2\n"Layer0"\n{\n'
            '    shader "shaders/hc1_veridant_pool_v2.shader"\n'
            '    TextureNormalA "materials/belltower/fountain_water_normal.png"\n'
            '    TextureNormalB "materials/belltower/fountain_water_normal.png"\n'
            '    g_vWaterColor "[0.035 0.085 0.073]"\n'
            '    g_flAbsorptionDistance "90"\n'
            '    g_flWaterRoughness "0.065"\n}\n')


def _stone(m, lo, hi, paint, seed, bevel=.22):
    """Closed coping slab with small bevels and restrained, uneven arrises."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    rng = np.random.default_rng(seed)
    e0, n0, z0 = lo; e1, n1, z1 = hi
    turn = rng.uniform(.26, .56, 4)
    outline = [(e0+turn[0], n0), (e1-turn[1], n0), (e1, n0+turn[1]),
               (e1, n1-turn[2]), (e1-turn[2], n1), (e0+turn[3], n1),
               (e0, n1-turn[3]), (e0, n0+turn[0])]
    perimeter = []
    for a, b in zip(outline, outline[1:]+outline[:1]):
        a, b = np.asarray(a), np.asarray(b)
        for t in np.linspace(0, 1, max(2, int(np.linalg.norm(b-a)/4)), endpoint=False):
            perimeter.append(a*(1-t)+b*t)
    centre = (lo[:2]+hi[:2])/2
    top_dip = rng.uniform(.015, .07, len(perimeter))
    # A couple of small edge spalls, rather than random damage over every edge.
    for index in rng.choice(len(perimeter), size=2, replace=False):
        top_dip[index] += rng.uniform(.11, .24)
    loops = []
    for z, inset, dip in ((z0, bevel, 0), (z0+bevel, 0, 0), (z1-bevel, 0, 0), (z1, bevel, 1)):
        ring = []
        for index, point in enumerate(perimeter):
            direction = point-centre
            point = point-direction/np.maximum(np.abs(direction), 1)*inset
            ring.append(v(*point, z-top_dip[index]*dip))
        loops.append(ring)
    for lower, upper in zip(loops, loops[1:]):
        for i in range(len(perimeter)):
            j = (i+1) % len(perimeter)
            m.polygon(paint, [lower[i], lower[j], upper[j], upper[i]])
    centre_top = v(*centre, z1-.035)
    for i, point in enumerate(loops[-1]):
        m.polygon(paint, [centre_top, point, loops[-1][(i+1)%len(perimeter)]], normal=UP)
    m.polygon(paint, list(reversed(loops[0])), normal=-UP)


def _sphere(subdivisions):
    t = (1+5**.5)/2
    points = np.asarray([(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),(0,-1,t),(0,1,t),
                         (0,-1,-t),(0,1,-t),(t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)], float)
    points /= np.linalg.norm(points, axis=1)[:,None]
    points = list(points)
    faces = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),
             (11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
             (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
    for _ in range(subdivisions):
        cache = {}; new = []
        def mid(a, b):
            key = tuple(sorted((a,b)))
            if key not in cache:
                q = points[a]+points[b]; q /= np.linalg.norm(q)
                cache[key] = len(points); points.append(q)
            return cache[key]
        for a,b,c in faces:
            ab,bc,ca = mid(a,b),mid(b,c),mid(c,a)
            new.extend(((a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)))
        faces = new
    return np.asarray(points), np.asarray(faces)


def _clip(rows, z, above):
    result = []
    for a,b in zip(rows, rows[1:]+rows[:1]):
        ina = a[0][2] >= z if above else a[0][2] <= z
        inb = b[0][2] >= z if above else b[0][2] <= z
        if ina: result.append(a)
        if ina != inb:
            t = (z-a[0][2])/(b[0][2]-a[0][2])
            result.append(tuple(x*(1-t)+y*t for x,y in zip(a,b)))
    return result


def _rock(m, centre, radius, seed, squash, water_z, subdivisions):
    original = K.Model()
    P.boulder(original, centre, radius, seed=seed, squash=squash, paint='vr_rock_dark')
    hull = np.asarray(original.hulls[0][0])
    origin = hull.mean(axis=0)
    halfspaces = ConvexHull(hull-origin).equations
    directions, faces = _sphere(subdivisions)
    denom = directions @ halfspaces[:,:3].T
    with np.errstate(divide='ignore', invalid='ignore'):
        distances = np.where(denom > 1e-8, -halfspaces[:,3]/denom, np.inf)
    old_radius = distances.min(axis=1)
    rng = np.random.default_rng(700+seed)
    normals = np.asarray([(1,.2,.24),(-.8,.3,.35),(.2,1,.18),(-.2,-1,.24),
                          (.61,-.25,1),(-.48,-.4,.9),(.8,-.5,-.08)], float)
    normals += rng.normal(0,.08,normals.shape)
    normals /= np.linalg.norm(normals, axis=1)[:,None]
    support = (hull-origin) @ normals.T
    limits = support.max(axis=0)*np.asarray([.68,.76,.81,.72,.79,.89,.77])
    projected = directions @ normals.T
    with np.errstate(divide='ignore', invalid='ignore'):
        cuts = np.where(projected > 1e-8, limits/projected, 1e8)
    radii = np.minimum(old_radius*.995, -.32*logsumexp(-cuts/.32, axis=1))
    points = origin+directions*radii[:,None]
    # Small, correlated pitting and fracture notches change the actual silhouette.
    phase = points @ np.asarray((.31,.27,.37))
    noise = .09*np.sin(phase*1.9)*np.sin(points[:,1]*.38+1.1)
    fissure = np.exp(-((points @ np.asarray((.32,.88,.18))-np.dot(origin,(.32,.88,.18))-radius*.14)/.55)**2)
    radii = np.minimum(old_radius*.996, radii+noise-.48*fissure)
    points = origin+directions*radii[:,None]
    vertex_normals = np.zeros_like(points)
    for a,b,c in faces:
        normal = np.cross(points[b]-points[a], points[c]-points[a])
        vertex_normals[[a,b,c]] += normal
    vertex_normals /= np.maximum(np.linalg.norm(vertex_normals,axis=1)[:,None],1e-9)
    uv = np.column_stack(((np.arctan2(directions[:,1], directions[:,0])/(2*math.pi)+.5),
                           .5+np.arcsin(directions[:,2])/math.pi))
    for face in faces:
        face_uv = uv[face].copy()
        if np.ptp(face_uv[:,0]) > .5: face_uv[face_uv[:,0]<.5,0] += 1
        face_uv *= (max(1.3, radius/18), max(.7,radius/32))
        rows = [(points[i],vertex_normals[i],face_uv[j]) for j,i in enumerate(face)]
        for paint, bottom, top in (('vr_pool_rock_wet',-1000,water_z-.25),
                                    ('vr_pool_rock_damp',water_z-.25,water_z+1.0),
                                    ('vr_pool_rock',water_z+1.0,1000)):
            clipped = _clip(_clip(rows,bottom,True),top,False)
            if len(clipped) < 3: continue
            m.polygon(paint, [r[0] for r in clipped], normals=[r[1] for r in clipped], uv=[r[2] for r in clipped])
    # Exactly the source collision, even when the entire map is regenerated.
    m.hulls.extend(original.hulls)
    residual = (points-origin) @ halfspaces[:,:3].T+halfspaces[:,3]
    assert residual.max() <= 1e-6
    return {'seed':seed,'vertices':len(points),'triangles':len(faces),
            'inside_original_collision':True,'bounds':[points.min(axis=0).tolist(),points.max(axis=0).tolist()]}


def build_into(m, water, bounds, kerb_z, water_z):
    p0,p1,n0,n1 = bounds; k = 12.
    first_box = len(m.boxes); first_hull = len(m.hulls)
    # Retain the old rectangular collisions; edge wear is purely visual.
    for a,b,c,d in ((p0,p1,n0,n0+k),(p0,p1,n1-k,n1),
                    (p0,p0+k,n0+k,n1-k),(p1-k,p1,n0+k,n1-k)):
        m.collision_box((a,c,0),(b,d,kerb_z-1.5),'default')
        m.collision_box((a-1.2,c-1.2,kerb_z-1.5),(b+1.2,d+1.2,kerb_z),'default')
        # Recessed mortar occupies each small stone-to-stone gap.
        P.box(m,a+.14,b-.14,c+.14,d-.14,.1,kerb_z-.27,'vr_pool_joint',None)
    ranges = [(p0,p1,n0,n0+k,True),(p0,p1,n1-k,n1,True),
              (p0,p0+k,n0+k,n1-k,False),(p1-k,p1,n0+k,n1-k,False)]
    slabs = 0
    for side,(a,b,c,d,along_e) in enumerate(ranges):
        start,end = (a,b) if along_e else (c,d)
        count = max(1,round((end-start)/33))
        for i in range(count):
            t0 = start+(end-start)*i/count+.07
            t1 = start+(end-start)*(i+1)/count-.07
            lo = (t0,c,.05) if along_e else (a,t0,.05)
            hi = (t1,d,kerb_z-3.4) if along_e else (b,t1,kerb_z-3.4)
            paint = ('vr_pool_coping','vr_pool_coping_light','vr_pool_coping','vr_pool_coping_dark')[(i+side)%4]
            _stone(m,lo,hi,paint,1000+side*100+i,bevel=.14)
            # The cap stays within the original overhanging lip's extent.
            ca,cb,cc,cd = a-1.2,b+1.2,c-1.2,d+1.2
            if along_e:
                low = ca if i == 0 else t0
                high = cb if i == count-1 else t1
                clo,chi = (low,cc,kerb_z-3.3),(high,cd,kerb_z)
            else:
                low = c+1.2+.07 if i == 0 else t0
                high = d-1.2-.07 if i == count-1 else t1
                clo,chi = (ca,low,kerb_z-3.3),(cb,high,kerb_z)
            _stone(m,clo,chi,paint,2000+side*100+i,bevel=.25)
            slabs += 1
    # Visible basin floor: large quiet green-grey stone slabs, not a black card.
    a,b,c,d = p0+k,p1-k,n0+k,n1-k
    P.box(m,a,b,c,d,.21,.30,'vr_pool_joint',None)
    nx,ny = 7,6
    for i in range(nx):
        for j in range(ny):
            e0,e1 = a+(b-a)*i/nx+.065,a+(b-a)*(i+1)/nx-.065
            nn0,nn1 = c+(d-c)*j/ny+.065,c+(d-c)*(j+1)/ny-.065
            card(m,'vr_pool_liner',[v(e0,nn0,.34),v(e1,nn0,.34),v(e1,nn1,.34),v(e0,nn1,.34)],UP)
    card(water,'vr_pool',[v(a,c,water_z),v(b,c,water_z),v(b,d,water_z),v(a,d,water_z)],UP)
    rocks = [_rock(m,(10.,-40.,0.),46,3,.62,water_z,5),
             _rock(m,(-55.,22.,0.),26,4,.5,water_z,4)]
    # Existing fixtures and light positions stay at their source values.
    for aa,bb,out in (((p0-.6,n0-.6),(p1+.6,n0-.6),(0,-1)),
                      ((p0-.6,n1+.6),(p1+.6,n1+.6),(0,1)),
                      ((p0-.6,n0),(p0-.6,n1),(-1,0)),((p1+.6,n0),(p1+.6,n1),(1,0))):
        P.led(m,(*aa,kerb_z-2.3),(*bb,kerb_z-2.3),v(*out,0),1.)
    P.LIGHTS.append(('Pool light',(70.,-60.,water_z-4),P.WARM,150,False))
    for index,n in enumerate((-70.,50.)):
        P.wall_washer(m,f'Pool kerb light {index}',(p1,n,8.),(1,0),160,light=index==0,size=(5.,3.),rise=8)
    m.material_overrides.update(MATERIALS)
    m.tile_overrides.update({paint:54. if 'coping' in paint else 38. for paint in MATERIALS})
    return {'coping_sections':slabs,'basin_tiles':nx*ny,'rocks':rocks,
            'boxes':len(m.boxes)-first_box,'hulls':len(m.hulls)-first_hull,
            'footprint':list(bounds),'water_z':water_z}
