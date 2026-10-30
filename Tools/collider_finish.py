"""Collider's maintained laboratory finish: real surface scans and fabricated junctions.

Everything in this module is visual. Player collision, door logic, lights and gameplay
placement remain owned by collider_map. The live migration uses the current published
mesh rather than regenerating it, so unrelated editor work is retained.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import map_kit as K
import boxyard_map as B
from belltower_furniture import bevel_box, face

ROOT = Path(__file__).resolve().parents[1]
MATERIAL_DIR = "materials/collider/finish-v1"
PAINTS = ("cf_floor", "cf_soffit", "cf_wall", "cf_edge", "cf_frame",
          "cf_stainless", "cf_gasket", "cf_wear", "cf_concrete")
TILES = dict(zip(PAINTS, (192., 192., 192., 192., 64., 32., 24., 1., 256.)))
UP = np.array((0., 0., 1.))
AXES = np.eye(3)
SCAN = "materials/spillway/scans/"


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint] = f"{MATERIAL_DIR}/{paint}.vmat"
            model.tile_overrides[paint] = TILES[paint]
    if "ar_hazard" in model.polygons:
        import ares_materials
        model.material_overrides["ar_hazard"] = "materials/ares/ar_hazard.vmat"
        model.tile_overrides["ar_hazard"] = ares_materials.TILES["ar_hazard"]
    return model


def surface_paint(paint, normal):
    if paint == "co_floor":
        return "cf_floor" if normal[2] > .8 else "cf_soffit" if normal[2] < -.8 else "cf_edge"
    return {"co_wall": "cf_wall", "co_concrete": "cf_concrete"}.get(paint, paint)


def refine_structure(model):
    """Separate walking surfaces, concrete soffits and exposed slab edges."""
    replacement = K.Model()
    for paint, polygons in model.polygons.items():
        for index, (points, normal) in enumerate(polygons):
            name = surface_paint(paint, normal)
            replacement.polygon(name, points, normal,
                uv=model.polygon_uvs.get((paint, index)),
                normals=model.polygon_normals.get((paint, index)))
    model.polygons = replacement.polygons
    model.polygon_uvs = replacement.polygon_uvs
    model.polygon_normals = replacement.polygon_normals
    configure(model)


def block(model, lo, hi, paint="cf_frame", bevel=.25):
    lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
    bevel_box(model, (lo+hi)/2, AXES, hi-lo, paint, bevel)


def fastener(model, at, normal, radius=.28):
    """Low dome and a recessed drive; no oversized decorative hex bolts."""
    at, normal = np.asarray(at, float), np.asarray(normal, float)
    u = np.cross(normal, UP if abs(normal[2]) < .9 else (0., 1., 0.))
    u = K.normalise(u)
    v = np.cross(normal, u)
    B.lathe(model, at, normal, [(radius, 0), (radius, .045),
            (radius*.85, .10), (radius*.42, .135)], "cf_stainless", sides=12, cap="cf_stainless")
    # The drive is an actual dark recess on the crown, under 2 mm wide.
    c = at+normal*.136
    face(model, "cf_gasket", [c-u*.12-v*.025, c+u*.12-v*.025,
        c+u*.12+v*.025, c-u*.12+v*.025], normal)


def door_frame(model, axis, r0, r1, d0, d1, z0, z1, depth=3., width=8.):
    """Replace the old square portal stock with closed, chamfered fabricated parts."""
    def p(r, d, z):
        return np.array((r, d, z) if axis == "e" else (d, r, z))
    for da, db in ((d0-depth, d0), (d1, d1+depth)):
        for ra, rb, za, zb in ((r0-width, r0, z0, z1+width),
                (r1, r1+width, z0, z1+width), (r0, r1, z1, z1+width)):
            block(model, p(ra, da, za), p(rb, db, zb), "cf_frame", .48)
        # Preserve the established hazard boots exactly, including their envelope.
        for ra, rb in ((r0-width, r0), (r1, r1+width)):
            model.box(p(ra, da-.2 if da < d0 else da, z0),
                      p(rb, db+.2 if db > d1 else db, z0+24), "ar_hazard")
        sign = -1 if da < d0 else 1
        front = da if sign < 0 else db
        normal = np.array((0., sign, 0.)) if axis == "e" else np.array((sign, 0., 0.))
        for r in (r0-width*.5, r1+width*.5):
            for z in (z0+36, z0+112, z1-16):
                fastener(model, p(r, front+sign*.01, z), normal, .34)
        for r in (r0+14, r1-14):
            fastener(model, p(r, front+sign*.01, z1+width*.5), normal, .34)
        # Separate gasket behind each leaf-facing jamb: a readable material break.
        for ra, rb in ((r0-.22, r0+.08), (r1-.08, r1+.22)):
            block(model, p(ra, front-sign*.25, z0+25),
                p(rb, front-sign*.02, z1-.4), "cf_gasket", .035)


def portals():
    for s in (-1, 1):
        for z, ns in ((0., (-650., 0., 480.)), (256., (-650., 480.))):
            for n in ns:
                yield "n", n-88, n+88, s*1412-12, s*1412+12, z, z+192
    for e in (-900., 900.):
        yield "e", e-80, e+80, 650., 674., 0., 192.


def subtract(run, gaps):
    spans = [run]
    for lo, hi in gaps:
        spans = [(a, min(b, lo)) for a, b in spans if a < lo] + [
                 (max(a, hi), b) for a, b in spans if b > hi]
    return [(a, b) for a, b in sorted(spans) if b-a > 3]


def cove(model, a, b, facing, z):
    """A closed stainless/painted cove, filleted where the floor meets the wall."""
    a, b = np.array((*a, z)), np.array((*b, z))
    inward = np.array((*facing, 0.), float)
    # Radius at the foot is 1.15 inches; rear flange lies against the wall.
    profile = [(0.025, .06), (1.18, .06)]
    for angle in np.linspace(-math.pi/2, -math.pi, 7)[1:]:
        profile.append((1.18+1.12*math.cos(angle), 1.18+1.12*math.sin(angle)))
    profile += [(.06, 7.65), (.20, 7.82), (.20, 8.05), (.025, 8.05)]
    for (u0, v0), (u1, v1) in zip(profile, profile[1:]+profile[:1]):
        points = [a+inward*u0+UP*v0, b+inward*u0+UP*v0,
                  b+inward*u1+UP*v1, a+inward*u1+UP*v1]
        normal = np.cross(b-a, inward*(u1-u0)+UP*(v1-v0))
        # The extrusion's winding is corrected against the outward profile normal.
        outward = inward*(v1-v0)-UP*(u1-u0)
        face(model, "cf_frame", points, outward)
    # The rolled section is concave. Ear clipping closes each end without a fan
    # crossing the fillet or creating reversed triangles at the return flange.
    for end, sign in ((a, -1), (b, 1)):
        for triangle in triangulate_profile(profile):
            face(model, "cf_frame", [end+inward*profile[i][0]+UP*profile[i][1]
                 for i in triangle], (b-a)*sign)
    # Narrow shadow seam at the top keeps trim from reading as a painted stripe.
    lo = a+inward*.012+UP*8.05
    hi = b+inward*.035+UP*8.22
    model.box(np.minimum(lo, hi), np.maximum(lo, hi), "cf_gasket")


def triangulate_profile(points):
    points=np.asarray(points,float)
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    area=sum(cross(points[i],points[(i+1)%len(points)]) for i in range(len(points)))
    direction=1 if area>0 else -1
    remaining=list(range(len(points)));triangles=[]
    while len(remaining)>3:
        for k,index in enumerate(remaining):
            a,b,c=remaining[k-1],index,remaining[(k+1)%len(remaining)]
            pa,pb,pc=points[[a,b,c]]
            if cross(pb-pa,pc-pb)*direction<=1e-10:continue
            def inside(q):
                return min(cross(pb-pa,q-pa)*direction,cross(pc-pb,q-pb)*direction,
                           cross(pa-pc,q-pc)*direction)>=-1e-10
            if any(inside(points[j]) for j in remaining if j not in (a,b,c)):continue
            triangles.append((a,b,c));remaining.pop(k);break
        else:raise ValueError('Cove profile cannot be triangulated')
    triangles.append(tuple(remaining))
    return triangles


def cove_runs():
    ground_gaps = [(n-97, n+97) for n in (-650, 0, 480)]
    upper_gaps = [(n-97, n+97) for n in (-650, 480)]
    for z, gaps in ((0., ground_gaps), (256., upper_gaps)):
        for s in (-1, 1):
            for n0, n1 in subtract((-899., 649.), gaps):
                yield (s*1400, n0), (s*1400, n1), (-s, 0), z
                yield (s*1424, n0), (s*1424, n1), (s, 0), z
            outer = [(-899., 979.)] if z == 0 else [(-899., -781.), (-139., 649.)]
            for n0, n1 in outer:
                yield (s*1900, n0), (s*1900, n1), (-s, 0), z
        yield (-1898., -900.), (1898., -900.), (0, 1), z
    for e0, e1 in subtract((-1399., 1399.), [(-990, -810), (810, 990)]):
        yield (e0, 650.), (e1, 650.), (0, -1), 0.
    yield (-1329., 650.), (1329., 650.), (0, -1), 256.
    yield (-1898., 980.), (1898., 980.), (0, -1), 0.


def threshold(model, axis, r0, r1, d0, d1, z0, z1):
    def p(r, d, z): return np.array((r,d,z) if axis == "e" else (d,r,z))
    mid = (d0+d1)/2
    # Flush screwed service plate: visible relief is under 5 mm, no blocking lip.
    block(model, p(r0+1.5, mid-18, z0+.018), p(r1-1.5, mid+18, z0+.18), "cf_stainless", .045)
    for d in (mid-14, mid+14):
        block(model, p(r0+3, d-.085, z0+.181), p(r1-3, d+.085, z0+.19), "cf_gasket", .025)
    for r in (r0+8, (r0+r1)/2, r1-8):
        for d in (mid-10, mid+10):
            fastener(model, p(r, d, z0+.19), UP, .23)


def decal(model, center, right, up, size, tile):
    center, right, up = np.asarray(center), np.asarray(right), np.asarray(up)
    normal = np.cross(right, up)
    w,h = size
    points = [center-right*w/2-up*h/2, center+right*w/2-up*h/2,
              center+right*w/2+up*h/2, center-right*w/2+up*h/2]
    u,v = (tile%4)/4, 1-(tile//4+1)/4
    face(model, "cf_wear", points, normal,
         [(u,v), (u+.25,v), (u+.25,v+.25), (u,v+.25)])


def wear(model):
    rng=np.random.default_rng(42765)
    for index,(axis,r0,r1,d0,d1,z,z1) in enumerate(portals()):
        middle=(r0+r1)/2
        for side in (-1,1):
            if axis == "n":
                center=np.array(((d0+d1)/2+side*67,middle+rng.uniform(-12,12),z+.045))
                right=np.array((0.,1.,0.));along=np.array((-1.,0.,0.))
            else:
                center=np.array((middle+rng.uniform(-12,12),(d0+d1)/2+side*67,z+.045))
                right=np.array((1.,0.,0.));along=np.array((0.,1.,0.))
            decal(model,center,right,along,(116,144),8+index%4)
        # Light trolley scuffs adjacent to the jamb, rather than sprayed on every wall.
        front=(d0-3.05 if index%2 else d1+3.05)
        sign=-1 if index%2 else 1
        if axis == "n":
            c=(front,r1+25,z+28); r=(0.,sign,0.)
        else:
            c=(r1+25,front,z+28); r=(-sign,0.,0.)
        decal(model,c,r,UP,(42,40),12+index%4)
    # Restrained traces along actual circulation routes. No cards span the open atrium.
    routes=[((-1660,-540),(-1660,510),0),((1660,-560),(1660,500),0),
            ((-1100,-500),(900,-500),0),((-1100,170),(1100,170),0),
            ((-1200,820),(1200,820),0),
            ((-1190,-500),(-1190,490),256),((1190,-490),(1190,490),256),
            ((-900,-730),(900,-730),256),((-850,450),(850,450),256)]
    for a,b,z in routes:
        a,b=np.array(a),np.array(b);delta=b-a;length=np.linalg.norm(delta)
        along=delta/length;right=np.array((along[1],-along[0]))
        for step in range(max(2,int(length/130))):
            t=(step+.5)/max(2,int(length/130))
            c=a+delta*t+right*rng.uniform(-24,24)
            angle=math.atan2(along[1],along[0])+rng.uniform(-.45,.45)
            u=np.array((math.cos(angle),math.sin(angle),0.))
            v=np.cross(UP,u)
            decal(model,(*c,z+.047),u,v,(20,13),int(rng.integers(0,8)))


def surface_context(models):
    """Recover actual floor, soffit and luminaire planes from authored geometry."""
    floors=set();ceilings=set();lamps=set()
    for number,source in enumerate(models):
        for paint,polygons in source.polygons.items():
            for points,normal in polygons:
                points=np.asarray(points)
                if abs(normal[2])<.99:continue
                lo,hi=points.min(0),points.max(0)
                if abs(hi[2]-lo[2])>.002:continue
                rect=tuple(round(float(v),3) for v in (*lo[:2],*hi[:2],lo[2]))
                if number==0 and paint in ('co_floor','cf_floor') and normal[2]>.99:floors.add(rect)
                if paint in ('co_floor','cf_soffit','co_steel') and normal[2]<-.99:ceilings.add(rect)
                if paint=='co_white' and normal[2]<-.99 and max(hi[:2]-lo[:2])>=50 and min(hi[:2]-lo[:2])<=6:
                    lamps.add(rect)
    return {'floors':sorted(floors),'ceilings':sorted(ceilings),'lamps':sorted(lamps)}


def fixture_mounts(model,context):
    """Threaded droppers and ceiling shoes support the existing suspended LED bars."""
    for e0,n0,e1,n1,bottom in context['lamps']:
        center=np.array(((e0+e1)/2,(n0+n1)/2,bottom+4.5))
        axis=0 if e1-e0>n1-n0 else 1
        half=(e1-e0 if axis==0 else n1-n0)/2-7
        for side in (-1,1):
            point=center.copy();point[axis]+=side*half
            hits=[r[4] for r in context['ceilings'] if r[0]<=point[0]<=r[2] and r[1]<=point[1]<=r[3] and r[4]>point[2]+2]
            if not hits:continue
            ceiling=min(hits)
            if ceiling-point[2]>180:continue
            B.lathe(model,point,UP,[(.20,0),(.20,ceiling-point[2]-.3)],'cf_stainless',sides=10,cap='cf_stainless')
            block(model,(point[0]-2.4,point[1]-1.65,ceiling-.36),
                  (point[0]+2.4,point[1]+1.65,ceiling-.03),'cf_frame',.08)
            for z in (point[2]+.12,ceiling-.8):
                B.lathe(model,(point[0],point[1],z),UP,[(.48,0),(.48,.28)],'cf_stainless',sides=6,cap='cf_stainless')


def add_finish(model,context=None):
    context=context or surface_context([model])
    fixture_mounts(model,context)
    for a,b,facing,z in cove_runs(): cove(model,a,b,facing,z)
    for p in portals(): threshold(model,*p)
    wear(model)
    configure(model)


def vmat(color,normal=None,rough=None,rough_value=.75,metalness=0.,tint=(1,1,1),alpha=None,ao=None,scale=1.):
    lines=['// Tools/collider_finish.py','"Layer0"','{','    shader "shaders/complex.shader"','    F_SPECULAR "1"']
    if alpha:
        lines += ['    F_TRANSLUCENT "1"', f'    TextureTranslucency "{alpha}"']
    lines += [f'    TextureColor "{color}"',f'    TextureNormal "{normal or "materials/default/default_normal.tga"}"',
        f'    TextureRoughness "{rough or f"[{rough_value} {rough_value} {rough_value} 0]"}"',
        f'    TextureAmbientOcclusion "{ao or "materials/default/default_ao.tga"}"',
        f'    g_flMetalness "{metalness}"','    g_flRoughnessScaleFactor "1"',
        f'    g_vTexCoordScale "[{scale:.8f} {scale:.8f}]"',
        f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"','    g_flModelTintAmount "1"','}']
    return '\n'.join(lines)+'\n'


def materials(out):
    """Reuse photographed, already local PBR scans; author only the paint and wear atlas."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    cast='concrete_wall_009'
    for name,scan,tint,rough in (
        ('cf_soffit',cast,(.77,.80,.82),.93),
        ('cf_wall',cast,(.82,.87,.89),.79),
        ('cf_edge',cast,(.61,.66,.69),.88),
        ('cf_concrete',cast,(.82,.87,.89),.79)):
        text=vmat(SCAN+scan+'_diff_2k.jpg',MATERIAL_DIR+'/'+scan+'_nor_gl_2k.jpg',
            SCAN+scan+'_rough_2k.jpg' if rough is None else None,
            rough_value=rough or .8,tint=tint,scale=TILES[name]/(1805/25.4))
        (out/(name+'.vmat')).write_text(text,encoding='utf-8')
    # The photographed floor covers two metres, not a five-metre generic wall tile.
    # Keep its native normal, roughness and AO registered to the same photograph.
    import json
    source=ROOT/'Sources/Collider/finish-v1/scans'
    manifest=json.loads((source/'manifest.json').read_text())
    for entry in manifest['files']:
        (out/entry['file']).write_bytes((source/entry['file']).read_bytes())
    (out/'cf_floor.vmat').write_text(vmat(
        f'{MATERIAL_DIR}/hangar_concrete_floor_diff_2k.jpg',
        f'{MATERIAL_DIR}/hangar_concrete_floor_nor_gl_2k.png',
        f'{MATERIAL_DIR}/hangar_concrete_floor_rough_2k.png',
        tint=(1.55,1.62,1.64),ao=f'{MATERIAL_DIR}/hangar_concrete_floor_ao_2k.png',
        scale=TILES['cf_floor']/(2000/25.4)),encoding='utf-8')
    # Fine powder-coat microtexture; no coarse clouds or uniformly painted edge chips.
    rng=np.random.default_rng(9821);n=1024
    grain=rng.standard_normal((n,n)).astype(np.float32)
    image=np.clip(np.array((67,79,82))[None,None,:]+grain[...,None]*1.3,0,255).astype(np.uint8)
    Image.fromarray(image).save(out/'paint_color.png')
    Image.fromarray(np.uint8(np.clip(.63+grain*.012,0,1)*255)).save(out/'paint_rough.png')
    (out/'cf_frame.vmat').write_text(vmat(f'{MATERIAL_DIR}/paint_color.png',
        rough=f'{MATERIAL_DIR}/paint_rough.png'),encoding='utf-8')
    (out/'cf_stainless.vmat').write_text(vmat('[0.24 0.27 0.28 1]',rough_value=.62,metalness=.80),encoding='utf-8')
    (out/'cf_gasket.vmat').write_text(vmat('[0.025 0.029 0.028 1]',rough_value=.91),encoding='utf-8')
    atlas=Image.new('L',(1024,1024))
    for tile in range(16):
        rng=np.random.default_rng(81000+tile)
        stamp=Image.new('L',(256,256));d=ImageDraw.Draw(stamp)
        if tile<8:
            # Partial footwear transfer, faded heel and segmented tread.
            for y in range(68,189,13):
                half=int(17+11*math.sin((y-50)/150*math.pi))
                for side in (-1,1):
                    x=126+side*(half//2)
                    d.rounded_rectangle((x-half//2,y,x+half//2,y+5),radius=2,fill=int(rng.integers(13,35)))
            d.ellipse((107,182,145,207),fill=18)
            stamp=stamp.rotate(float(rng.uniform(-18,18)),resample=Image.Resampling.BICUBIC)
        elif tile<12:
            # Turning wheel arcs and soft scuff patches outside door thresholds.
            for k in range(13):
                x=int(rng.integers(46,155));y=int(rng.integers(30,120));rad=int(rng.integers(45,100))
                d.arc((x-rad,y-rad,x+rad,y+rad),int(rng.integers(20,70)),int(rng.integers(115,175)),
                      fill=int(rng.integers(9,28)),width=int(rng.integers(1,4)))
            for k in range(40):
                x,y=rng.integers(45,211,2);d.line((int(x),int(y),int(x+12),int(y+3)),fill=int(rng.integers(5,16)),width=1)
        else:
            for k in range(48):
                x,y=rng.integers(48,208,2);length=rng.uniform(6,38)
                d.line((int(x),int(y),int(x+length),int(y+rng.uniform(-2,2))),
                       fill=int(rng.integers(8,31)),width=int(rng.integers(1,4)))
            stamp=stamp.filter(ImageFilter.GaussianBlur(.45))
        data=np.asarray(stamp,dtype=np.float32)
        breakup=np.clip(rng.standard_normal(data.shape)*.45+.55,0,1)
        data*=breakup
        # An explicit zero alpha border prevents rectangular patch outlines in mips.
        data[:8]=data[-8:]=0;data[:,:8]=data[:,-8:]=0
        stamp=Image.fromarray(data.astype(np.uint8))
        atlas.paste(stamp,((tile%4)*256,(tile//4)*256))
    atlas.save(out/'wear_alpha.png')
    (out/'cf_wear.vmat').write_text(vmat('[0.12 0.13 0.12 1]',rough_value=.86,
        alpha=f'{MATERIAL_DIR}/wear_alpha.png'),encoding='utf-8')
    return [p for p in sorted(out.iterdir()) if p.suffix in ('.png','.jpg','.vmat')]
