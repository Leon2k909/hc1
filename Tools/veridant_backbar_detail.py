"""Authored resort back bar. Plan-space inches; render detail, no collision.

The glass/labels have explicit UVs and smooth normals. Cabinet board grain is
oriented along each real board, not whichever edge an individual face happens
to have. Stocks form small product families, with space for working barware.
"""
import math
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
import map_kit as K
import riverdale_parts as P

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'materials/veridant/backbar-v2'
NAMES = ('walnut', 'walnut_dark', 'brass', 'steel', 'glass_green', 'glass_amber',
         'glass_clear', 'liquid_red', 'liquid_amber', 'foil_dark', 'foil_gold',
         'foil_red', 'labels', 'backing', 'led', 'cork')
MATERIALS = {f'vr_backbar_{n}': f'{PREFIX}/{n}.vmat' for n in NAMES}
X = np.array((1., 0., 0.)); Y = np.array((0., 1., 0.)); Z = np.array((0., 0., 1.))

# Height, half-width, rounded-square exponent, glass, cap and label.
FAMILIES = (
    (12.0, 1.36, 2., 'green', 'dark', 0),    # Bordeaux
    (11.4, 1.48, 2., 'green', 'gold', 1),    # broad Burgundy
    (9.7, 1.61, 4.6, 'clear', 'dark', 2),   # square botanical gin
    (9.1, 1.64, 4., 'clear', 'gold', 3),    # bourbon flask
    (11.6, 1.32, 2., 'amber', 'dark', 4),   # tall rum
    (10.8, 1.42, 2., 'amber', 'red', 5),    # aperitivo
    (8.5, 1.66, 2., 'green', 'gold', 6),    # squat liqueur
    (8.9, 1.66, 5., 'clear', 'dark', 7),    # cut shoulder decanter
)


def lighting_specs(lo,hi,z0,face='+e'):
    """Small practical LED pools, with no shadow-map or frame callbacks."""
    e0,n0=lo;e1,n1=hi
    out=np.array({'+e':(1.,0.,0.),'-e':(-1.,0.,0.),'+n':(0.,1.,0.),'-n':(0.,-1.,0.)}[face])
    right=np.cross(Z,out)
    width=n1-n0 if face.endswith('e') else e1-e0
    front=np.array(((e1 if face=='+e' else e0) if face.endswith('e') else (e0+e1)/2,
                    (n1 if face=='+n' else n0) if face.endswith('n') else (n0+n1)/2,z0))
    bays=3 if width>84 else 2 if width>43 else 1;bw=(width-3)/bays
    rows=[]
    for bay in range(bays):
        u=-width/2+1.5+(bay+.5)*bw
        for h in ((67.,88.) if bays==3 and bay==1 else (52.,70.,88.)):
            pos=front+right*u-out*1.7+Z*h
            rows.append({'name':f'Backbar LED {n0:g} bay {bay} shelf {h:g}',
                         'position':pos.tolist(),'color':'0.90,0.75,0.55,1','radius':34.,'shadows':False})
    return rows


def apply_baked_probe(node,name):
    """Reuse the reviewed room captures after a full source regeneration."""
    cache=ROOT/'Sources/Veridant/backbar-v2/lighting-installed.json'
    if cache.exists():
        path=json.loads(cache.read_text()).get('probe_textures',{}).get('Probe '+name)
        if path:
            c=node['Components'][0]
            c.pop('RenderDynamically',None)
            c.update({'Mode':'Baked','BakedTexture':path,'__version':1})
    return node


def section(a, exponent):
    c, s = math.cos(a), math.sin(a)
    xy = np.array((math.copysign(abs(c)**(2/exponent), c),
                   math.copysign(abs(s)**(2/exponent), s)))
    normal = np.sign(xy) * np.abs(xy)**(exponent-1)
    return xy, normal / np.linalg.norm(normal)


def vessel(m, centre, profile, paint, sides=32, exponent=2., caps=True, yaw=0., flute=0.):
    """Turn a closed profile, including return walls for open glassware.

    Derivatives are evaluated in profile order (including descending inner
    walls), so inner faces point into a vessel instead of smoothing outward.
    """
    centre = np.array(centre); rings = []; normals = []
    ca, sa = math.cos(yaw), math.sin(yaw)
    turn = np.array(((ca, -sa), (sa, ca)))
    last = max(p[0] for p in profile)
    for j, (h, r) in enumerate(profile):
        prev = np.array(profile[max(0, j-1)])
        nxt = np.array(profile[min(len(profile)-1, j+1)])
        dh, dr = nxt-prev
        if abs(dh)+abs(dr) < 1e-8: dh = 1
        pts = []; ns = []
        for a in np.linspace(0, math.tau, sides, endpoint=False):
            xy, nn = section(a, exponent)
            rib = 1 + flute * math.cos(a*12) * max(0, 1-h/max(last, .01))
            xy = turn @ xy; nn = turn @ nn
            pts.append(centre + np.array((xy[0]*r*rib, xy[1]*r*rib, h)))
            ns.append(P.unit((nn[0]*dh, nn[1]*dh, -dr)))
        rings.append(pts); normals.append(ns)
    for j in range(len(rings)-1):
        for i in range(sides):
            k = (i+1) % sides
            uv = [(i/sides, 1-profile[j][0]/max(last,.01)),
                  ((i+1)/sides, 1-profile[j][0]/max(last,.01)),
                  ((i+1)/sides, 1-profile[j+1][0]/max(last,.01)),
                  (i/sides, 1-profile[j+1][0]/max(last,.01))]
            ns = [normals[j][i], normals[j][k], normals[j+1][k], normals[j+1][i]]
            P.card(m, paint, [rings[j][i], rings[j][k], rings[j+1][k], rings[j+1][i]],
                   sum(ns), uv=uv, normals=ns)
    if caps:
        P.card(m, paint, rings[0], -Z)
        P.card(m, paint, rings[-1], Z)


def label(m, centre, radius, exponent, yaw, low, high, tile, neck=False):
    """A conforming, physically separate paper wrap with printed foil mask."""
    ca, sa = math.cos(yaw), math.sin(yaw)
    turn = np.array(((ca, -sa), (sa, ca)))
    aa = np.linspace(math.radians(37), math.radians(143), 17)
    curve=np.array([section(a,exponent)[0] for a in aa])
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))]
    distance/=distance[-1]
    col, row = tile % 4, tile // 4
    for i, (a,b) in enumerate(zip(aa[:-1], aa[1:])):
        xya, na = section(a, exponent); xyb, nb = section(b, exponent)
        xya = turn @ xya; xyb = turn @ xyb
        na = turn @ na; nb = turn @ nb
        pts = [np.array(centre)+np.array((xy[0]*(radius+.018),xy[1]*(radius+.018),h))
               for xy,h in ((xya,low),(xyb,low),(xyb,high),(xya,high))]
        # Rounded-square faces have a nonuniform arc per angle. Arc-length UVs
        # retain the printed lettering's spacing across their wide flat front.
        u0, u1 = distance[i], distance[i+1]
        # Source OBJ V is flipped by ModelDoc; high source V is image top.
        ys = (.94,.94,.06,.06) if not neck else (.22,.22,.06,.06)
        uv = [((col+.94-.88*t)/4,1-(row+y)/4) for t,y in zip((u0,u1,u1,u0),ys)]
        P.card(m,'vr_backbar_labels',pts,(*((na+nb)/2),0),uv=uv,
               normals=[(*na,0),(*nb,0),(*nb,0),(*na,0)])


def bottle(m,u,d,z,rng,family,scale=1.,yaw=None):
    h,r,exponent,glass,cap,tile = FAMILIES[family]
    h *= scale; r *= scale
    yaw = rng.uniform(-.27,.27) if yaw is None else yaw
    shoulder = (.67,.53,.64,.59,.66,.70,.49,.58)[family]
    neck = (.31,.32,.36,.39,.30,.31,.40,.43)[family]
    # Curved heels and distinct shoulders, with enough rings to retain a smooth
    # highlight at close range without over-tessellating hidden liquid surfaces.
    prof = [(0,r*.83),(.08,r*.94),(.20,r*.995),(.38,r),
            (h*shoulder-.28,r),(h*shoulder,r*.995),
            (h*(shoulder+.048),r*.94),(h*(shoulder+.094),r*.78),
            (h*(shoulder+.134),r*.53),(h*(shoulder+.16),r*neck*1.08),
            (h-.9,r*neck),(h-.38,r*neck),(h-.30,r*neck*1.15),
            (h-.19,r*neck*1.15)]
    assert all(b[0] > a[0] for a,b in zip(prof,prof[1:])),family
    vessel(m,(u,d,z),prof,'vr_backbar_glass_'+glass,exponent=exponent,yaw=yaw)
    # Thick optical heel and the shoulder's glass thickness can be read around
    # the fill. Liquid has a shallow meniscus instead of an opaque painted core.
    if family not in (2,6):
        fill = h*rng.uniform(.60,.66)
        liquid = 'red' if family in (0,1,5) else 'amber'
        fill_radius=float(np.interp(fill,[p[0] for p in prof],[p[1] for p in prof]))-.09
        liquid_profile=[(hh,rr-.09) for hh,rr in prof if .20<=hh<fill-.10]
        liquid_profile += [(fill-.025,fill_radius),(fill,fill_radius-.025)]
        vessel(m,(u,d,z),liquid_profile,'vr_backbar_liquid_'+liquid,
               exponent=exponent,sides=24,yaw=yaw)
    nr = r*neck*1.16
    foil_bottom = h-(1.27 if family in (0,1) else .69)
    vessel(m,(u,d,z),[(foil_bottom,nr*.97),(foil_bottom+.07,nr),
           (h-.05,nr),(h,nr*.92)],'vr_backbar_foil_'+cap,sides=24)
    # Rolled cap and tamper seal, very small real geometry.
    vessel(m,(u,d,z),[(h-.21,nr*1.012),(h-.17,nr*1.012)],'vr_backbar_brass',sides=24)
    if family == 7:
        vessel(m,(u,d,z),[(h-.02,nr*.87),(h+.15,nr*.80),(h+.39,nr*.90),
               (h+.47,nr*.82)],'vr_backbar_cork',sides=20)
    label(m,(u,d,z),r,exponent,yaw,h*.19,h*(.52 if family not in (1,6) else .45),tile)
    if family in (0,1,4):
        label(m,(u,d,z),nr*.88,2.,yaw,h-1.7,h-1.30,8+family%4,neck=True)
    return h


def glass(m,u,d,z,kind='rocks'):
    if kind == 'rocks':
        # A thick heavy base, rounded lip and visible interior wall.
        prof=[(0,.91),(.06,1.02),(.22,1.08),(2.9,1.22),(3.06,1.20),
              (3.10,1.15),(3.04,1.10),(.46,.98),(.38,.94)]
    elif kind == 'coupe':
        prof=[(0,.98),(.05,1.08),(.12,1.04),(.20,.41),(.32,.13),
              (3.7,.12),(3.82,.39),(4.0,.84),(4.35,1.31),(4.70,1.49),
              (4.77,1.49),(4.80,1.44),(4.69,1.42),(4.39,1.25),(4.10,.78),(3.98,.25)]
    else:
        prof=[(0,1.02),(.05,1.09),(.13,1.02),(.24,.19),(.37,.11),
              (3.4,.11),(3.58,.25),(3.72,.53),(3.9,.82),(4.2,1.1),
              (4.5,1.27),(4.9,1.38),(5.3,1.43),(5.7,1.40),(6.1,1.30),
              (6.5,1.16),(6.72,1.08),(6.8,1.03),(6.82,1.00),
              (6.76,.97),(6.5,1.09),(6.1,1.23),(5.7,1.33),(5.3,1.36),
              (4.9,1.31),(4.5,1.20),(4.2,1.03),(3.96,.74),(3.84,.44)]
    vessel(m,(u,d,z),prof,'vr_backbar_glass_clear',sides=32,caps=True)


def serving_set(m,u,d,z,rng):
    P.bevel_box(m,(u,d,z+.07),(X,Y,Z),(11.8,6.1,.14),'vr_backbar_brass',bevel=.06)
    # A raised thin rim bounds the metal tray; the glasses sit on its real base.
    for side in (-1,1):
        P.bevel_box(m,(u+side*5.83,d,z+.29),(X,Y,Z),(.12,6.,.48),'vr_backbar_brass',bevel=.045)
        P.bevel_box(m,(u,d+side*2.94,z+.29),(X,Y,Z),(11.7,.12,.48),'vr_backbar_brass',bevel=.045)
    glass(m,u-3.8,d-.4,z+.15,'rocks');glass(m,u-.9,d+.1,z+.15,'rocks')
    # Three-piece shaker and a double-ended jigger, turned with real lips.
    vessel(m,(u+3,d-.35,z+.15),[(0,1.10),(.09,1.19),(.23,1.23),
           (5.5,1.54),(5.65,1.54),(5.8,1.47),(6.1,1.42),
           (6.65,.75),(6.75,.64),(7.25,.64),(7.31,.58)],'vr_backbar_steel',sides=32)
    vessel(m,(u+1.3,d+1.8,z+.15),[(0,.66),(.09,.69),(1.33,.31),
           (1.48,.31),(3.,.91),(3.04,.87),(2.90,.80),(1.65,.28)],
           'vr_backbar_steel',sides=20,caps=False)


def build_into(model,lo,hi,z0,face='+e'):
    e0,n0=lo;e1,n1=hi
    out=np.array({'+e':(1.,0.,0.),'-e':(-1.,0.,0.),'+n':(0.,1.,0.),'-n':(0.,-1.,0.)}[face])
    right=np.cross(Z,out)
    width=n1-n0 if face.endswith('e') else e1-e0
    depth=e1-e0 if face.endswith('e') else n1-n0
    front=np.array(((e1 if face=='+e' else e0) if face.endswith('e') else (e0+e1)/2,
                    (n1 if face=='+n' else n0) if face.endswith('n') else (n0+n1)/2,z0))
    axes=np.array((right,out,Z));local=K.Model()
    seed=int(abs(e0*7+n0*3))%1000;rng=np.random.default_rng(seed)
    counts={'bottles':0,'glasses':0,'serving_sets':0,'families':set()}

    def wood(centre,size,bevel=.065,grain=Z,paint='walnut'):
        mat='vr_backbar_'+paint;start=len(local.polygons[mat]);centre=np.array(centre)
        P.bevel_box(local,centre,(X,Y,Z),size,mat,bevel=bevel)
        shift=rng.uniform(.40,.60,2)
        for index in range(start,len(local.polygons[mat])):
            points,normal=local.polygons[mat][index]
            along=grain-normal*np.dot(normal,grain)
            if np.linalg.norm(along)<.1:along=X if abs(normal[0])<.8 else Y
            along=P.unit(along);across=P.unit(np.cross(normal,along))
            coords=np.array([(np.dot(p-centre,across),np.dot(p-centre,along)) for p in points])
            limits=np.maximum(np.ptp(coords,axis=0)*1.45,(28.,112.))
            local.polygon_uvs[(mat,index)]=[tuple(p/limits+shift) for p in coords]

    def metal(centre,size,paint='brass',bevel=.035):
        P.bevel_box(local,centre,(X,Y,Z),size,'vr_backbar_'+paint,bevel=bevel)

    # Modern fitted joinery, plinth shadow gap, fine brass reveals. Pieces are
    # straight where they are made straight; realism comes from construction.
    bays=3 if width>84 else 2 if width>43 else 1
    bay_width=(width-3)/bays
    wood((0,-depth+.42,45),(width,.84,90),paint='walnut_dark')
    for side in (-1,1):
        wood((side*(width/2-.75),-depth/2,45),(1.5,depth,90),bevel=.11)
        metal((side*(width/2-.48),.025,45),(.10,.08,89.2))
    wood((0,-depth/2,89.3),(width,depth,1.4),grain=X,bevel=.10)
    wood((0,-depth/2,2),(width-.6,depth-1.4,4),paint='walnut_dark',grain=X)
    wood((0,-depth/2,34.35),(width,depth,1.30),grain=X,bevel=.11)
    metal((0,.035,33.51),(width-2,.09,.10))
    for bay in range(bays):
        u=-width/2+1.5+(bay+.5)*bay_width
        # The bronze-green backing is a quiet satin surface behind the stock.
        metal((u,-depth+1.03,62),(bay_width-.18,.16,52.7),'backing',.025)
        for leaf in (-1,1):
            du=u+leaf*bay_width/4;dw=bay_width/2-.17
            wood((du,-.35,18.75),(dw,.78,28.9),bevel=.07)
            # Slender vertical pulls; their mounts sit on the door face.
            handle=du-leaf*(dw/2-1.30)
            for hh in (21.,26.):
                P.rod(local,(handle,.07,hh),(handle,.62,hh),.09,'vr_backbar_brass',8,True)
            P.rod(local,(handle,.62,20.9),(handle,.62,26.1),.13,'vr_backbar_brass',12,True)
        if bay:
            divider=-width/2+1.5+bay*bay_width
            wood((divider,-depth/2,62.15),(1.,depth,52.9),bevel=.08)
            metal((divider,.025,62.1),(.08,.08,52.5))
        working = bays==3 and bay==1
        levels=(35.,68.) if working else (35.,53.,71.)
        for level,h in enumerate(levels):
            if level:
                wood((u,-depth/2,h-.48),(bay_width-.1,depth,.96),grain=X,bevel=.08)
                metal((u,.018,h-.95),(bay_width-.8,.07,.10))
            # Diffuser recessed under the shelf above, facing down. It is not a
            # bright white bar stuck on the front of every wooden board.
            above=levels[level+1] if level+1<len(levels) else 89.
            metal((u,-1.7,above-.86),(bay_width-2,.43,.16),'walnut_dark',.025)
            P.card(local,'vr_backbar_led',[(u-bay_width/2+1.4,-1.9,above-.95),
                   (u+bay_width/2-1.4,-1.9,above-.95),(u+bay_width/2-1.4,-1.55,above-.95),
                   (u-bay_width/2+1.4,-1.55,above-.95)],-Z)
            if working and level==0:
                serving_set(local,u+bay_width*.19,-4.7,h+.025,rng)
                counts['serving_sets']+=1;counts['glasses']+=2
                positions=(u-bay_width*.32,u-bay_width*.19)
                families=(7,3)
            else:
                amount=max(2,int((bay_width-6)/5.8))
                # Product groups, with unequal gaps and depth. Stock is not
                # placed one identical bottle per equal-width slot.
                span=(amount-1)*3.85+1.0
                start=u-span/2+rng.uniform(-1.2,.8)
                positions=[start+i*3.85+(1.0 if i>=amount//2 else 0) for i in range(amount)]
                primary=(bay*3+level*2+seed)%8
                families=[(primary+(i//2)*2)%8 for i in range(amount)]
            for i,(bu,family) in enumerate(zip(positions,families)):
                bd=-rng.uniform(3.2,4.6)
                bottle(local,bu+rng.uniform(-.13,.13),bd,h+.035,rng,family,scale=rng.uniform(.98,1.02))
                counts['bottles']+=1;counts['families'].add(family)
            # Short front row of tumblers/coupes breaks up just a few stock
            # groups. All bases remain planted on the actual shelf surface.
            if not working and level==1 and bay_width>30:
                glass(local,u+bay_width*.34,-2.45,h+.025,'coupe')
                counts['glasses']+=1
        if working:
            # Two pairs of inverted hanging stem glasses, open rails supporting
            # their feet, comfortably below the central high shelf.
            for gu in (u-6.0,u-1.2,u+3.6,u+8.4):
                cup=K.Model();glass(cup,0,0,0,'wine')
                for paint,rows in cup.polygons.items():
                    for i,(points,normal) in enumerate(rows):
                        transform=np.array(((1.,0.,0.),(0.,-1.,0.),(0.,0.,-1.)))
                        ns=cup.polygon_normals.get((paint,i))
                        P.card(local,paint,[p@transform+np.array((gu,-5.,66.6)) for p in points],normal@transform,
                               normals=[n@transform for n in ns] if ns is not None else None,
                               uv=cup.polygon_uvs.get((paint,i)))
                for side in (-1,1):
                    rail=gu+side*.68
                    metal((rail,-5.,66.39),(.24,7.3,.14),'brass',.04)
                    for end in (-8.35,-1.65):
                        metal((rail,end,66.75),(.24,.30,.66),'brass',.035)
                counts['glasses']+=1
            # A small printed drinks card in a brass foot, rather than an empty
            # billboard. Atlas tile 12 carries the resort's fictional menu.
            metal((u-2.5,-7.0,35.10),(5.0,2.6,.16))
            P.card(local,'vr_backbar_labels',[(u-4.7,-6.95,35.2),(u-.3,-6.95,35.2),
                   (u-.3,-7.7,43.0),(u-4.7,-7.7,43.0)],Y,
                   uv=[(.02,.01),(.23,.01),(.23,.24),(.02,.24)])
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p:12. for p in MATERIALS})
    for paint,rows in local.polygons.items():
        for index,(points,normal) in enumerate(rows):
            ns=local.polygon_normals.get((paint,index))
            P.card(model,paint,[front+p@axes for p in points],normal@axes,
                   normals=[n@axes for n in ns] if ns is not None else None,
                   uv=local.polygon_uvs.get((paint,index)))
    lights=lighting_specs(lo,hi,z0,face)
    P.LIGHTS.extend((s['name'],tuple(s['position']),s['color'],s['radius'],s['shadows']) for s in lights)
    return {**counts,'families':sorted(counts['families']),'bays':bays,'width':width,'depth':depth,
            'shelf_lights':len(lights)}


def maps(out):
    rng=np.random.default_rng(814503)
    source=ROOT/'Sources/Veridant/backbar-v2/walnut-albedo-generated.png'
    # The generator's original is archived unchanged. Normalize the runtime
    # texture dimensions for Source 2's power-of-two normal mip filter.
    image=Image.open(source).convert('RGB').resize((2048,2048),Image.Resampling.LANCZOS)
    image.save(out/'walnut_color.png')
    rgb=np.asarray(image,float)/255
    grey=rgb.mean(axis=2);n=grey.shape[0]
    pore=grey-gaussian_filter(grey,2.2)
    dx=(np.roll(pore,-1,1)-np.roll(pore,1,1))*.11
    dy=(np.roll(pore,-1,0)-np.roll(pore,1,0))*.11
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/'walnut_normal.png')
    rough=np.clip(.45-.13*pore+.035*(grey-grey.mean()),.38,.54)
    Image.fromarray(np.uint8(rough*255)).save(out/'walnut_rough.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    n=512;y,x=np.mgrid[:n,:n]
    grain=gaussian_filter(rng.normal(size=(n,n)),(.6,12))
    grain/=max(grain.std(),1e-8)
    cloud=gaussian_filter(rng.normal(size=(n,n)),22);cloud/=cloud.std()
    metal=(1+.025*grain+.025*cloud)[...,None]*np.array((178.,147.,96.))
    Image.fromarray(np.uint8(np.clip(metal,0,255))).save(out/'brass_color.png')
    Image.fromarray(np.uint8(np.clip(.31+.035*grain+.025*cloud,.22,.44)*255)).save(out/'brass_rough.png')
    Image.fromarray(np.uint8(np.clip(.19+.03*grain+.025*cloud,.11,.30)*255)).save(out/'steel_rough.png')
    glass=np.clip(.09+.014*cloud+.009*grain,.06,.14)
    Image.fromarray(np.uint8(glass*255)).save(out/'glass_rough.png')
    Image.fromarray(np.uint8(np.clip(.31+.035*grain,.24,.39)*255)).save(out/'foil_rough.png')
    Image.fromarray(np.uint8(np.clip(.62+.025*cloud,.54,.70)*255)).save(out/'backing_rough.png')


def label_atlas(out):
    """Fictional packaging: distinct typographic systems, foil and paper masks."""
    n=2048;atlas=Image.new('RGB',(n,n),(221,211,185));foil=Image.new('L',(n,n),0)
    rough=Image.new('L',(n,n),178);d=ImageDraw.Draw(atlas);f=ImageDraw.Draw(foil);rd=ImageDraw.Draw(rough)
    font=lambda s,b=False:ImageFont.truetype('C:/Windows/Fonts/georgiab.ttf' if b else 'C:/Windows/Fonts/georgia.ttf',s)
    sans=lambda s:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',s)
    titles=('ALTO','COSTA','JUNIPER','AMBRE','SALVO','ROSSO','VERDE','NO. 8',
            'RISERVA','VIGNETO','EST. 1924','BARREL 12','VERIDANT','RIVA','MORA','SOLERA')
    palettes=[((225,215,187),(62,39,40)),((34,48,62),(217,202,163)),
              ((214,221,204),(34,60,48)),((30,39,38),(200,161,91)),
              ((219,208,176),(65,42,30)),((113,30,34),(226,209,167)),
              ((226,216,184),(49,74,43)),((26,36,46),(215,180,108))]
    gold=(176,137,66)
    for tile,title in enumerate(titles):
        xx=(tile%4)*512;yy=(tile//4)*512
        paper,ink=palettes[tile%8]
        if tile==12:paper,ink=(36,48,48),(221,207,166)
        d.rectangle((xx,yy,xx+511,yy+511),fill=paper)
        def line(coords,fill=ink,width=2,metal=False):
            points=[(xx+x,yy+y) for x,y in coords];d.line(points,fill=fill,width=width)
            if metal:f.line(points,fill=210,width=width);rd.line(points,fill=93,width=width)
        def text(x,y,s,ft,fill=ink,metal=False):
            pos=(xx+x,yy+y);d.text(pos,s,font=ft,fill=fill,anchor='mm')
            if metal:f.text(pos,s,font=ft,fill=205,anchor='mm');rd.text(pos,s,font=ft,fill=101,anchor='mm')
        # Double rules and corner details deliberately vary by product family.
        for margin,w in ((28,3),(38,1)):
            line(((margin,margin),(512-margin,margin),(512-margin,512-margin),
                  (margin,512-margin),(margin,margin)),fill=gold,width=w,metal=True)
        if tile==12:
            text(256,90,title,font(39,True));text(256,137,'APERITIVO',sans(22))
            line(((80,174),(432,174)),fill=gold,metal=True)
            for k,s in enumerate(('Spritz della casa','Botanical tonic','Riviera negroni','Vino della costa')):
                text(256,218+k*49,s,font(21))
            text(256,449,'AT THE WATER\'S EDGE',sans(15));continue
        text(256,74,'TENUTA DELLA COSTA' if tile%2==0 else 'DISTILLERIA ARTIGIANA',sans(17))
        text(256,155,title,font(55 if len(title)<8 else 39,True),metal=tile in (1,3,5,7))
        # Fine ornamental botanical engraving, not the same printed badge on
        # every product. Stems, leaves and a small crest stay readable close up.
        if tile%3==0:
            for side in (-1,1):
                line([(256+side*(40+8*k),318-9*k) for k in range(11)],width=2)
                for k in range(1,10):
                    sx=256+side*(40+8*k);sy=318-9*k
                    line(((sx,sy),(sx+side*14,sy-17),(sx+side*20,sy-12)),width=2)
            text(256,275,'A' if tile%2==0 else 'S',font(67))
        elif tile%3==1:
            for radius in (58,63):
                d.ellipse((xx+256-radius,yy+274-radius,xx+256+radius,yy+274+radius),outline=gold,width=2)
            text(256,273,'12' if tile==4 else 'C',font(63))
            for side in (-1,1):line(((256+side*84,271),(256+side*145,271)),fill=gold,metal=True)
        else:
            for branch in range(5):
                angle=-1.1+branch*.55
                end=(256+85*math.sin(angle),302-72*math.cos(angle))
                line(((256,323),end),width=2)
                for j in range(1,6):
                    q=j/6;sx=256+(end[0]-256)*q;sy=323+(end[1]-323)*q
                    d.ellipse((xx+sx-4,yy+sy-4,xx+sx+4,yy+sy+4),outline=ink,width=2)
        sub=('ROSSO RISERVA','BIANCO DELLA RIVA','BOTANICAL DRY GIN','SINGLE BARREL',
             'AGED CARIBBEAN RUM','APERITIVO AMARO','LIQUORE ALLE ERBE','RESERVE BLEND')[tile%8]
        text(256,367,sub,font(22,True));text(256,409,'PRODOTTO E IMBOTTIGLIATO IN ITALIA',sans(12))
        line(((81,435),(431,435)),fill=gold,width=1,metal=True)
        text(256,460,'750 ml    •    '+('13.5% VOL' if tile%8<2 else '40% VOL')+'    •    LOT 024',sans(13))
        for k in range(11):
            x=224+k*6
            line(((x,483),(x,495)),width=1 if k%3 else 2)
    atlas.save(out/'labels_color.png');foil.save(out/'labels_metal.png');rough.save(out/'labels_rough.png')


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True);maps(out);label_atlas(out)
    colours={'walnut':(1.,1.,1.),'walnut_dark':(.72,.72,.68),'brass':(1.,1.,1.),
             'steel':(.63,.66,.68),'foil_dark':(.050,.055,.047),'foil_gold':(.66,.47,.20),
             'foil_red':(.28,.035,.032),'backing':(.13,.17,.15),'cork':(.32,.23,.13)}
    glass={'glass_green':(.61,.74,.42),'glass_amber':(.86,.67,.39),'glass_clear':(.94,.96,.94),
           'liquid_red':(.54,.23,.16),'liquid_amber':(.82,.57,.25)}
    for name in NAMES:
        if name in glass:
            tint=glass[name]
            text=('// Tools/veridant_backbar_detail.py\n"Layer0"\n{\n    shader "shaders/glass.shader"\n'
                  '    F_GLASS_QUALITY "2"\n    g_bFogEnabled "1"\n    g_flBlurAmount "0.02"\n'
                  f'    g_flRefractionStrength "{1.012 if name.startswith("glass") else 1.002}"\n'
                  '    AlbedoAbsorption "0.20"\n    g_flTintColor "[1 1 1 0]"\n'
                  f'    TextureColor "[{tint[0]} {tint[1]} {tint[2]} 0]"\n'
                  f'    TextureNormal "{PREFIX}/flat_normal.png"\n    TextureRoughness "{PREFIX}/glass_rough.png"\n'
                  '    TextureMetalness "[0 0 0 0]"\n    TextureAmbientOcclusion "[1 1 1 0]"\n'
                  '    TextureTranslucency "[1 1 1 0]"\n    TextureBlendMask "[0 0 0 0]"\n    TextureTintMask "[1 1 1 0]"\n}\n')
        else:
            wood=name.startswith('walnut')
            colour=f'{PREFIX}/walnut_color.png' if wood else f'{PREFIX}/labels_color.png' if name=='labels' else f'{PREFIX}/brass_color.png' if name=='brass' else 'materials/default/default_color.tga'
            normal=f'{PREFIX}/walnut_normal.png' if wood else f'{PREFIX}/flat_normal.png'
            rough=f'{PREFIX}/walnut_rough.png' if wood else f'{PREFIX}/labels_rough.png' if name=='labels' else f'{PREFIX}/brass_rough.png' if name=='brass' else f'{PREFIX}/steel_rough.png' if name=='steel' else f'{PREFIX}/foil_rough.png' if name.startswith('foil') else f'{PREFIX}/backing_rough.png'
            tint=colours.get(name,(1.,1.,1.))
            metal=f'{PREFIX}/labels_metal.png' if name=='labels' else '[0.88 0.88 0.88 0]' if name in ('brass','steel') else '[0.4 0.4 0.4 0]' if name.startswith('foil') else '[0 0 0 0]'
            scalar_metal=.88 if name in ('brass','steel') else .4 if name.startswith('foil') else 0
            illum=('    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1 1 1 0]"\n'
                   '    g_flSelfIllumBrightness "0.6"\n    g_flSelfIllumAlbedoFactor "1"\n'
                   '    g_vSelfIllumTint "[1 0.70 0.40 0]"\n') if name=='led' else ''
            text=('// Tools/veridant_backbar_detail.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'+illum+
                  f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
                  f'    TextureMetalness "{metal}"\n    g_flMetalness "{scalar_metal}"\n    g_flRoughnessScaleFactor "1"\n'
                  '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                  f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
