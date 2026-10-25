"""Physical grocery display revision: textured goods, varied silhouettes and groups.

This builds visual geometry only. The existing facade, glass plane and gameplay
collision are owned by the map. All randomness is local and reproducible.
"""
import math
import zlib
import numpy as np
import belltower_furniture as F
from map_kit import Model
from belltower_shop_displays import glass_properties as base_glass_properties

RESOURCE = 'materials/belltower/shop-display-v2'
# Colour values are also consumed by the construction renderer.
COLOURS = {
    'shop2_green': ((.075, .16, .035, 1), .22, 0),
    'shop2_amber': ((.29, .13, .026, 1), .23, 0),
    'shop2_liquid': ((.075, .054, .022, 1), .27, 0),
    'shop2_ceramic': ((.85, .79, .63, 1), .31, 0),
    'shop2_blue': ((.055, .075, .095, 1), .32, 0),
    'shop2_tin': ((.66, .65, .59, 1), .52, .84),
    'shop2_paper': ((1, 1, 1, 1), .94, 0),
    'shop2_rope': ((.42, .29, .15, 1), .92, 0),
    'shop2_onion': ((.69, .55, .31, 1), .77, 0),
    'shop2_wood': ((.57, .43, .28, 1), .90, 0),
    'shop2_wood_edge': ((.46, .34, .22, 1), .91, 0),
    'shop2_iron': ((.09, .085, .072, 1), .61, .65),
    'shop2_labels': ((1, 1, 1, 1), .87, 0),
    'shop2_prices': ((1, 1, 1, 1), .94, 0),
}


def glass_properties():
    result=base_glass_properties()
    result.update(F_DO_NOT_CAST_SHADOWS=1,
        TextureNormal='materials/default/default_normal.tga',g_flBlurAmount=0.0)
    return result


def glass_material_text():
    return '\n'.join(['// Tools/belltower_quality_materials.py; sources: Sources/Belltower/scans/manifest.json',
        '"Layer0"','{']+[f'    {k} "{v}"' for k,v in glass_properties().items()]+['}',''])


def material_path(name):
    return f'{RESOURCE}/{name.removeprefix("shop2_")}.vmat'


def properties(name):
    colour, roughness, metalness = COLOURS[name]
    result = {'shader': 'shaders/belltower_shop_display_v2.shader',
        'TextureColor': 'materials/default/default_color.tga',
        'TextureNormal': f'{RESOURCE}/surface_normal.png',
        'TextureRoughness': f'{RESOURCE}/surface_rough.png',
        'TextureAmbientOcclusion': 'materials/default/default_ao.tga',
        'g_vShopTint': '['+' '.join(map(str,colour[:3]))+']',
        'g_flShopRoughness': roughness, 'g_flShopMetalness': metalness,
        'g_flShopNormal': .22 if name.startswith('shop2_wood') else .35}
    # Filled bottles use an opaque glossy surface. Nested screen-space glass
    # behind the shop pane lost the bottle silhouettes in native validation.
    # Their shape, collars, label relief and roughness still supply real depth.
    if name.startswith('shop2_wood'):
        scan='materials/belltower/scans/brown_planks_03'
        result.update(TextureColor=scan+'_diffuse_4k.png',TextureNormal=scan+'_nor_gl_4k.png',
            TextureRoughness=scan+'_rough_4k.png',TextureAmbientOcclusion=scan+'_ao_4k.png')
    elif name == 'shop2_labels':
        result['TextureColor']=f'{RESOURCE}/labels-v2.png'
    elif name == 'shop2_prices':
        result['TextureColor']=f'{RESOURCE}/price-cards.png'
    elif name == 'shop2_paper':
        result['TextureColor']=f'{RESOURCE}/paper_color.png'
    elif name == 'shop2_tin':
        result['TextureColor']=f'{RESOURCE}/tin_color.png'
    return result


def material_text(name):
    return '\n'.join(['// Tools/belltower_shop_displays_v2.py','"Layer0"','{']+
        [f'    {k} "{v}"' for k,v in properties(name).items()]+['}',''])


def tile_uv(tile, u, v, columns=4, rows=4):
    # Keep the entire engraving while excluding neighbouring cell borders.
    inset=.013
    # Native complex's atlas sampling needs ascending local V. The row index
    # stays fixed so this changes label orientation without swapping products.
    # The map's local lateral basis runs opposite screen U when viewed from
    # outside. Counter that here, keeping the selected atlas cell unchanged.
    return ((tile%columns+1-inset-u*(1-2*inset))/columns,
            (tile//columns+inset+v*(1-2*inset))/rows)


def build(model, origin, outward, width, height):
    origin=np.asarray(origin,float);outward=np.asarray(outward,float)
    up=np.array((0.,0.,1.));right=np.cross(outward,up);inside=-outward
    axes=np.array((right,inside,up));half=width/2-4.4
    seed=zlib.crc32(','.join(f'{v:.3f}' for v in (*origin,*outward,width,height)).encode())
    rng=np.random.default_rng(seed)

    def at(q): return origin+np.asarray(q)@axes

    def box(centre,size,paint='shop2_wood',bevel=.12,yaw=0):
        a=math.radians(yaw)
        ax=np.array((right*math.cos(a)+inside*math.sin(a),
                     -right*math.sin(a)+inside*math.cos(a),up))
        timber=paint.startswith('shop2_wood')
        target=Model() if timber else model
        source=F.WOOD if timber else paint
        F.bevel_box(target,at(centre),ax,size,source,bevel,
                    seed+round(sum(v*w for v,w in zip(centre,(17,11,3)))))
        if timber:
            for i,(points,normal) in enumerate(target.polygons[source]):
                model.polygon(paint,points,normal,uv=target.polygon_uvs.get((source,i)))

    def beam(a,b,size,paint='shop2_rope'):
        F.beam(model,at(a),at(b),size,paint,.035,seed)

    def lathe(x,y,z,profile,paint,segments=18,lobes=0,cap=True):
        # Explicit local UVs and smooth normals survive OBJ export/mirroring.
        rings=[]
        slopes=[]
        for i in range(len(profile)):
            r0,z0=profile[max(0,i-1)];r1,z1=profile[min(len(profile)-1,i+1)]
            n=np.array((z1-z0,-(r1-r0)));slopes.append(n/np.linalg.norm(n))
        for r,h in profile:
            rings.append([np.array((x+math.cos(a)*r*(1+lobes*math.cos(6*a)),
                y+math.sin(a)*r*(1+lobes*math.cos(6*a)),z+h))
                for a in np.arange(segments)*math.tau/segments])
        for i,((r0,z0),(r1,z1)) in enumerate(zip(profile,profile[1:])):
            slope=np.array((z1-z0,-(r1-r0)));slope/=np.linalg.norm(slope)
            for k in range(segments):
                j=(k+1)%segments;a=k*math.tau/segments;b=(k+1)*math.tau/segments
                n0=(right*math.cos(a)+inside*math.sin(a))*slope[0]+up*slope[1]
                n1=(right*math.cos(b)+inside*math.sin(b))*slope[0]+up*slope[1]
                def vertex_normal(angle,ring):
                    return (right*math.cos(angle)+inside*math.sin(angle))*slopes[ring][0]+up*slopes[ring][1]
                pts=[at(rings[i][k]),at(rings[i][j]),at(rings[i+1][j]),at(rings[i+1][k])]
                uv=[(k/segments,z0/12),((k+1)/segments,z0/12),
                    ((k+1)/segments,z1/12),(k/segments,z1/12)]
                F.face(model,paint,pts,n0+n1,uv,[vertex_normal(a,i),vertex_normal(b,i),
                    vertex_normal(b,i+1),vertex_normal(a,i+1)])
        if cap:
            for points,sign in ((rings[0],-1),(rings[-1],1)):
                F.face(model,paint,[at(p) for p in points],up*sign)

    def wrap(x,y,z,r,h,tile,yaw=0,sweep=2.05):
        start=-math.pi/2-sweep/2+math.radians(yaw)
        end=start+sweep
        for a,b in zip(np.linspace(start,end,11)[:-1],np.linspace(start,end,11)[1:]):
            def p(angle,zz):return at((x+math.cos(angle)*r,y+math.sin(angle)*r,zz))
            n=right*math.cos((a+b)/2)+inside*math.sin((a+b)/2)
            u0,u1=(a-start)/sweep,(b-start)/sweep
            F.face(model,'shop2_labels',[p(a,z),p(b,z),p(b,z+h),p(a,z+h)],n,
                [tile_uv(tile,u0,0),tile_uv(tile,u1,0),tile_uv(tile,u1,1),tile_uv(tile,u0,1)])

    def flat_label(x,y,z,w,h,tile,yaw=0,price=False):
        a=math.radians(yaw);side=right*math.cos(a)+inside*math.sin(a)
        n=right*math.sin(a)-inside*math.cos(a);c=at((x,y,z))
        uv=(lambda u,v:tile_uv(tile,u,v,2,2)) if price else (lambda u,v:tile_uv(tile,u,v))
        F.face(model,'shop2_prices' if price else 'shop2_labels',
            [c-side*w/2,c+side*w/2,c+side*w/2+up*h,c-side*w/2+up*h],n,
            [uv(0,0),uv(1,0),uv(1,1),uv(0,1)])

    def bottle(x,y,z,h=19,r=2.3,tile=0,shape=0,yaw=0):
        body='shop2_green' if tile in (0,1,3) else 'shop2_amber'
        if shape%3==0:
            profile=[(r*.78,0),(r,.4),(r,h*.62),(r*.95,h*.69),
                (r*.68,h*.77),(r*.36,h*.83),(r*.36,h-.8),(r*.44,h-.65),(r*.44,h)]
        elif shape%3==1:
            profile=[(r*.85,0),(r,.5),(r,h*.54),(r*.90,h*.66),
                (r*.48,h*.73),(r*.42,h-.9),(r*.50,h-.8),(r*.50,h)]
        else:
            body='shop2_ceramic'
            profile=[(r*.84,0),(r,.6),(r,h*.65),(r*.94,h*.70),
                (r*.62,h*.80),(r*.38,h*.86),(r*.38,h-.7),(r*.44,h-.5),(r*.44,h)]
        lathe(x,y,z,profile,body,20)
        lathe(x,y,z+h-.25,[(r*.30,0),(r*.35,.8),(r*.29,1.05)],'shop2_rope',12)
        wrap(x,y,z+h*.15,r+.045,h*.30,tile,yaw)
        # A distinct thick base/collar gives glass real edge highlights.
        lathe(x,y,z+.4,[(r*1.015,0),(r*1.015,.21)],body,20)

    def jar(x,y,z,h=12,r=3,tile=8,yaw=0):
        profile=[(r*.86,0),(r,.5),(r*1.025,h*.65),(r*.99,h*.73),
                 (r*.88,h*.80),(r*.88,h*.86),(r*1.04,h*.88),(r*1.04,h*.94)]
        lathe(x,y,z,profile,'shop2_ceramic',20)
        lathe(x,y,z+h*.94,[(r*1.02,0),(r*1.05,.4),(r*.94,.7)],'shop2_blue',18)
        lathe(x,y,z+.7,[(r*1.012,0),(r*1.012,.22)],'shop2_blue',20)
        wrap(x,y,z+h*.18,r*1.03+.045,h*.38,tile,yaw)

    def tin(x,y,z,h=10,r=2.9,tile=4,yaw=0):
        lathe(x,y,z,[(r*.94,0),(r,.3),(r,h-.3),(r*.94,h)],'shop2_tin',18)
        wrap(x,y,z+.65,r+.04,h-1.3,tile,yaw,2.4)
        for offset in (.1,h-.3):
            lathe(x,y,z+offset,[(r*1.035,0),(r*1.04,.12),(r*1.035,.28)],'shop2_tin',18)
        lathe(x,y,z+h,[(r*.89,0),(r*.89,.12)],'shop2_tin',18)

    def packet(x,y,z,w=7,d=5,h=4,tile=6,yaw=0):
        box((x,y,z+h/2),(w,d,h),'shop2_paper',.27,yaw)
        a=math.radians(yaw)
        # The folded seam is offset from the body and has a tucked end.
        box((x,y+.1,z+h+.18),(w-.35,d*.65,.36),'shop2_paper',.12,yaw)
        flat_label(x+math.sin(a)*(d/2+.04),y-math.cos(a)*(d/2+.04),
            z+.28,w*.83,h*.82,tile,yaw)
        beam((x-.4,y-d/2-.12,z+.1),(x-.4,y-d/2-.12,z+h+.35),(.11,.11))
        beam((x-.4,y-d/2-.08,z+h+.4),(x-.4,y+d/2,z+h+.4),(.11,.11))

    def basket(x,y,z):
        # Coarse wicker strips have actual openings, a rolled rim and ribs.
        segments=24
        for row in range(5):
            za=.5+row*.76;zb=za+.46
            for k in range(segments):
                a,b=k*math.tau/segments,(k+1)*math.tau/segments
                def p(angle,h):return at((x+(6+h*.24)*math.cos(angle),
                    y+(4.0+h*.18)*math.sin(angle),z+h))
                n=right*math.cos((a+b)/2)+inside*math.sin((a+b)/2)
                pts=[p(a,za),p(b,za),p(b,zb),p(a,zb)]
                F.face(model,'shop2_rope',pts,n)
                F.face(model,'shop2_rope',list(reversed(pts)),-n)
        for k in range(16):
            a=k*math.tau/16
            beam((x+6*math.cos(a),y+4*math.sin(a),z+.2),
                 (x+7*math.cos(a),y+4.8*math.sin(a),z+4.2),(.19,.19))
        for k in range(segments):
            a,b=k*math.tau/segments,(k+1)*math.tau/segments
            beam((x+7*math.cos(a),y+4.8*math.sin(a),z+4.3),
                 (x+7*math.cos(b),y+4.8*math.sin(b),z+4.3),(.52,.52))
        for i,(dx,dy,dz) in enumerate(((-3,-1,2.4),(0,-1,2.3),(3,-1,2.3),
                (-2,1.4,2.6),(1.1,1.5,2.5),(-.4,-.1,4.6))):
            r=1.2+(i%3)*.11
            lathe(x+dx,y+dy,z+dz,[(.35,0),(r,.55),(r*1.05,1.2),
                (r*.72,2),(r*.20,2.65),(.10,3.1)],'shop2_onion',12,.07)
            beam((x+dx,y+dy,z+dz+2.8),(x+dx+.18,y+dy,z+dz+3.45),(.14,.14))

    # Individual rear boards and shelves. Their grain follows the joinery.
    # Solid backing closes the real board joints without coplanar faces.
    box((0,36.9,height/2),(width-1,1.0,height),bevel=.08)
    count=max(5,round(width/8))
    for i in range(count):
        span=(width-2)/count
        box((-(width-2)/2+(i+.5)*span,35.8,height/2),
            (span-.13,1.0,height-.2),bevel=.10)
    for x in (-half-2.2,half+2.2):
        box((x,19,height/2),(1.5,35,height))
    box((0,19,height-.7),(width-2,35,1.3))
    box((0,19,24.5),(width-2,35,1.3))
    # A small shaded fitting motivates the local display light, under the
    # existing external header. Its enclosure stays clear of the window frame.
    box((0,-2.2,height-2.6),(9.0,1.6,.85),'shop2_iron',.16)
    F.turned(model,at((-3.1,-2.2,height-3.35)),right,up,
        [(.26,0),(.37,.25),(.37,6.2),(.26,6.45)],'shop2_ceramic',14)
    for x in (-half+1.1,half-1.1):
        box((x,31,(height+25)/2),(2.1,3.2,height-26),bevel=.17)

    for row,shelf in enumerate((27.,51.8,76.8)):
        for k in range(3):
            box((0,14.5+k*7.2,shelf-.65),(half*2,7.05,1.3),bevel=.17)
        box((0,10.75,shelf-1.1),(half*2,.9,2.0),bevel=.20)
        # Restrained rubbed edge and recessed nail heads rather than white trim.
        for x in np.arange(-half+5,half-3,18):
            lathe_profile=[(.11,0),(.11,.07)]
            F.turned(model,at((x,10.24,shelf-.85)),-inside,right,
                     lathe_profile,'shop2_iron',8)
        groups=max(2,round(width/25))
        centres=np.linspace(-half+10,half-10,groups)
        for index,cx in enumerate(centres):
            x=cx+rng.uniform(-1.3,1.3);y=23+rng.uniform(-1.4,1.4)
            yaw=float(rng.uniform(-12,12))
            kind=(index+row*2+seed%3)%6
            if row==0 and index==min(1,groups-1):
                basket(x,18.7,shelf)
            elif kind==0:
                bottle(x-3.6,y+2.2,shelf,21,2.2,0,index,yaw)
                bottle(x+2.3,y+1.8,shelf,18,2.45,3,index+1,yaw-7)
                jar(x-1.0,y-4.3,shelf,8.0,2.1,10,yaw+8)
            elif kind==1:
                for j in range(3):packet(x+.35*j,y+.4*j,shelf+j*3.9,8,5.2,3.5,6 if j%2==0 else 15,yaw+3*j)
                bottle(x+6.0,y+1.6,shelf,17,2.15,2,2,yaw)
            elif kind==2:
                tin(x-3.2,y+1.5,shelf,12.2,2.9,4,yaw)
                tin(x+3.1,y+2.0,shelf,9.0,2.7,5,yaw-9)
                packet(x+.8,y-4.0,shelf,7,4.4,3.0,13,yaw+5)
            elif kind==3:
                jar(x-3.4,y+1.8,shelf,14,3.1,8,yaw)
                jar(x+3.5,y-1.8,shelf,10,2.7,9,yaw+11)
            elif kind==4:
                bottle(x-3.3,y+1.4,shelf,20,2.3,1,0,yaw)
                bottle(x+2.4,y-.8,shelf,16,2.6,2,1,yaw+10)
            else:
                tin(x-3.2,y+1.7,shelf,11.2,3,11,yaw)
                for j in range(3):packet(x+3,y-.2,shelf+j*3.35,7.1,5,3,12 if j<2 else 14,yaw-3*j)
        # Small shelf tickets attach to the front rail with a dark metal clip.
        for j,cx in enumerate(centres[::2]):
            yy=10.20;zz=shelf-1.6
            box((cx,yy-.015,zz+.72),(6.2,.12,2.5),'shop2_paper',.035)
            flat_label(cx,yy-.091,zz-.43,6.02,2.36,(j+row)%4,price=True)
            box((cx,yy-.12,zz+1.45),(.36,.17,.44),'shop2_iron',.04)
    for paint in COLOURS:
        model.material_overrides[paint]=material_path(paint)
        model.tile_overrides[paint]=12


def opening(model,wall,aperture):
    d,sign=wall.outer();outward=np.zeros(3)
    outward[1 if wall.axis=='e' else 0]=sign
    origin=wall.point((aperture.r0+aperture.r1)/2,d-sign*6,aperture.z0)
    build(model,origin,outward,aperture.r1-aperture.r0,aperture.z1-aperture.z0)
