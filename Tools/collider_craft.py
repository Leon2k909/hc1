"""Collider's round fabricated guardrails and shallow, located floor construction.

All detail stays in the established collision envelopes. The migration subtracts
real floor openings before adding recessed grates, covers and chipped concrete.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
import map_kit as K
import boxyard_map as B
import ares_map as A
import collider_finish as F
from belltower_furniture import bevel_box,beam

ROOT=Path(__file__).resolve().parents[1]
MATERIAL_DIR='materials/collider/craft-v1'
UP=np.array((0.,0.,1.))
PAINTS=('cc_rail','cc_hand','cc_metal','cc_seal','cc_raw')
TILES=dict(zip(PAINTS,(64.,64.,32.,32.,64.)))
FEATURES=(
    dict(name='west-coolant-drain',kind='grate',rect=(-700.,-684.,-470.,-310.),z=0.),
    dict(name='east-coolant-drain',kind='grate',rect=(684.,700.,-470.,-310.),z=0.),
    dict(name='gallery-access',kind='hatch',rect=(-1132.,-1048.,-285.,-215.),z=256.),
    dict(name='operations-access',kind='hatch',rect=(435.,525.,-725.,-655.),z=0.),
    dict(name='west-column-spall',kind='spall',rect=(-992.,-928.,-442.,-386.),z=0.),
    dict(name='east-column-spall',kind='spall',rect=(1024.,1072.,330.,372.),z=0.),
    dict(name='gallery-edge-spall',kind='spall',rect=(-1086.,-1046.,56.,94.),z=256.),
)
FEATURES+=tuple(dict(name=f'hall-joint-e-{e}',kind='joint',rect=(e-.11,e+.11,-880.,632.),z=0.)
    for e in (-900.,-300.,300.,900.))
FEATURES+=tuple(dict(name=f'hall-joint-n-{n}',kind='joint',rect=(-1380.,1380.,n-.11,n+.11),z=0.)
    for n in (-500.,100.,600.))
FEATURES+=tuple(dict(name=f'gallery-joint-{side}-{n}',kind='joint',
    rect=((-1390.,-1002.) if side<0 else (1002.,1390.))+(n-.11,n+.11),z=256.)
    for side in (-1,1) for n in (-500.,-100.,300.))


def configure(model):
    for paint in PAINTS:
        if paint in model.polygons:
            model.material_overrides[paint]=f'{MATERIAL_DIR}/{paint}.vmat'
            model.tile_overrides[paint]=TILES[paint]
    return F.configure(model)


def tube(model,a,b,radius,paint='cc_rail',sides=16,caps=True,phase=0.):
    """Closed circular tube, smooth normals and length/circumference UVs."""
    a,b=np.asarray(a,float),np.asarray(b,float)
    delta=b-a;length=np.linalg.norm(delta)
    if length<1e-5:return
    axis=delta/length;side=np.cross(UP,axis)
    if np.linalg.norm(side)<1e-6:side=np.array((1.,0.,0.))
    side=K.normalise(side);vertical=np.cross(axis,side)
    dirs=[side*math.cos(math.tau*i/sides)+vertical*math.sin(math.tau*i/sides) for i in range(sides)]
    rings=[[a+d*radius for d in dirs],[b+d*radius for d in dirs]]
    for i in range(sides):
        j=(i+1)%sides;v=i/sides;vv=(i+1)/sides
        B.card(model,paint,[rings[0][i],rings[0][j],rings[1][j],rings[1][i]],dirs[i]+dirs[j],
            uv=[(phase,v),(phase,vv),(phase+length/64,vv),(phase+length/64,v)],
            normals=[dirs[i],dirs[j],dirs[j],dirs[i]])
    if caps:
        B.card(model,paint,list(reversed(rings[0])),-axis)
        B.card(model,paint,rings[1],axis)


def collar(model,p,axis,radius,length=.28,paint='cc_rail'):
    p=np.asarray(p,float);axis=K.normalise(axis)
    B.lathe(model,p-axis*length/2,axis,[(radius*.84,0),(radius,length*.5),
        (radius*.84,length)],paint,sides=8)


def anchor(model,p,axis=UP,radius=.31):
    p=np.asarray(p,float);axis=np.asarray(axis,float)
    # A separate washer and hex nut retain useful silhouettes at player height.
    B.lathe(model,p,axis,[(radius*1.52,0),(radius*1.52,.09)],'cc_metal',sides=12,cap='cc_metal')
    B.lathe(model,p+axis*.10,axis,[(radius,.0),(radius,.34)],'cc_metal',sides=6,cap='cc_metal')


def base(model,p,along,side):
    bevel_box(model,p+UP*.22,(along,side,UP),(6.4,5.4,.44),'cc_rail',.14)
    # The black isolation pad seats against the slab instead of floating on it.
    model.oriented_box(p+UP*.055,(along,side,UP),(6.1,5.1,.11),'cc_seal')
    for aa in (-2.25,2.25):
        for ss in (-1.7,1.7):anchor(model,p+along*aa+side*ss+UP*.45)


def rail(model,a,b,z,lamps=False,collide=True):
    if collide:
        clip=K.Model();A.railing(clip,a,b,z,lamps=False,collide=True)
        model.boxes.extend(clip.boxes);model.hulls.extend(clip.hulls)
    a,b=np.array((*a,z),float),np.array((*b,z),float)
    length=np.linalg.norm(b-a)
    if length<4:return
    along=(b-a)/length;side=np.cross(UP,along)
    background=not collide and z==315
    phase=float(np.dot(a,(.011,.017,.003)))%11
    tube(model,a+UP*41,b+UP*41,1.48,'cc_hand',12 if background else 20,phase=phase)
    tube(model,a+UP*22,b+UP*22,.77,'cc_rail',8 if background else 12,phase=phase)
    # Thin folded toe board, with a rolled upper lip and real construction gaps.
    beam(model,a+UP*3,b+UP*3,(.28,5.8),'cc_rail',bevel=.1)
    tube(model,a+UP*5.9,b+UP*5.9,.15,'cc_rail',8)
    count=max(2,int(round(length/60))+1)
    seen=getattr(model,'_craft_posts',set());model._craft_posts=seen
    for i in range(count):
        p=a+(b-a)*i/(count-1);key=tuple(np.round(p,4))
        if key in seen:continue
        seen.add(key)
        if background:
            tube(model,p+UP*.45,p+UP*40.1,1.15,'cc_rail',10,phase=phase+i*.37)
            bevel_box(model,p+UP*.22,(along,side,UP),(6.4,5.4,.44),'cc_rail',.14)
            continue
        tube(model,p+UP*.45,p+UP*40.1,1.15,'cc_rail',16,phase=phase+i*.37)
        base(model,p,along,side)
        collar(model,p+UP*.85,UP,1.34,.42)
        collar(model,p+UP*39.7,UP,1.29,.30)
        for sign in (-1,1):collar(model,p+UP*22+along*sign*1.1,along,.91,.28)
        # A restrained, dark compression joint is shared by the manufactured run.
        if i and i%8==0:
            collar(model,p+UP*41+along*7,along,1.60,.7)
        if lamps and i%3==1:
            bevel_box(model,p+side*1.5+UP*31,(along,side,UP),(1.4,.8,3),'co_white',.1)


def slope_rail(model,a,b):
    a,b=np.asarray(a,float),np.asarray(b,float)
    direction=K.normalise((b-a)*np.array((1,1,0)));side=np.cross(UP,direction)
    tube(model,a+UP*38,b+UP*38,1.48,'cc_hand',20,phase=float(np.sum(a))%7)
    tube(model,a+UP*20,b+UP*20,.77,'cc_rail',12)
    length=np.linalg.norm((b-a)[:2]);count=max(2,round(length/60)+1)
    for i in range(count):
        p=a+(b-a)*i/(count-1)
        tube(model,p-UP*1.5,p+UP*37.3,1.15,'cc_rail',16,phase=i*.41)
        bevel_box(model,p+UP*3,(direction,side,UP),(5.6,.45,10),'cc_rail',.15)
        for dz in (0,6):anchor(model,p+UP*dz+side*.3,side,.32)
        collar(model,p+UP*36.8,UP,1.30,.32)
        for sign in (-1,1):collar(model,p+UP*20+direction*sign*1.1,direction,.91,.28)
    # Preserve the previous stair guard's exact collision authoring.
    model.beam(a+UP*40,b+UP*40,(3,10),None,'metal')


def floor_uv(p):
    return K.face_uv(K.to_world(p),UP,'cf_floor',K.uv_offset('collider_structure'),192.)


def clip(poly,axis,value,positive):
    if not poly:return []
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-value)*(1 if positive else -1);db=(b[axis]-value)*(1 if positive else -1)
        ina,inb=da>=-1e-8,db>=-1e-8
        if ina:result.append(a)
        if ina!=inb:result.append(a+(b-a)*(da/(da-db)))
    # Adjacent duplicates can otherwise produce zero-area fans at a cut corner.
    clean=[]
    for p in result:
        if not clean or np.linalg.norm(p[:3]-clean[-1][:3])>1e-7:clean.append(p)
    if len(clean)>1 and np.linalg.norm(clean[0][:3]-clean[-1][:3])<1e-7:clean.pop()
    return clean if len(clean)>=3 else []


def cut_floor(points,uv,features=FEATURES):
    polys=[[np.concatenate((p,t)) for p,t in zip(points,uv)]];changed=False
    for feature in features:
        if any(abs(p[2]-feature['z'])>1e-4 for p in points):continue
        x0,x1,y0,y1=feature['rect']
        next_polys=[]
        for poly in polys:
            bounds=np.array(poly)
            if bounds[:,0].max()<=x0 or bounds[:,0].min()>=x1 or bounds[:,1].max()<=y0 or bounds[:,1].min()>=y1:
                next_polys.append(poly);continue
            inside=poly;outside=[]
            for axis,value,positive in ((0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)):
                outside.extend([p] if (p:=clip(inside,axis,value,not positive)) else [])
                inside=clip(inside,axis,value,positive)
                if not inside:break
            if inside:changed=True;next_polys.extend(outside)
            else:next_polys.append(poly)
        polys=next_polys
    return polys,changed


def floor_face(model,paint,points,normal=UP):
    # Explicit UVs preserve the existing scan's position across newly cut surfaces.
    B.card(model,paint,points,normal,uv=[floor_uv(p) for p in points] if paint=='cf_floor' else None)


def floor_details(model):
    for index,f in enumerate(FEATURES):
        x0,x1,y0,y1=f['rect'];z=f['z'];center=np.array(((x0+x1)/2,(y0+y1)/2,z))
        width,height=x1-x0,y1-y0
        if f['kind']=='joint':
            B.card(model,'cc_seal',[(x0,y0,z-.2),(x1,y0,z-.2),(x1,y1,z-.2),(x0,y1,z-.2)],UP)
            for a,b in (((x0,y0,z),(x1,y0,z)),((x1,y0,z),(x1,y1,z)),
                        ((x1,y1,z),(x0,y1,z)),((x0,y1,z),(x0,y0,z))):
                a,b=np.array(a),np.array(b)
                B.card(model,'cc_raw',[a,b,b-UP*.2,a-UP*.2],np.cross(b-a,-UP))
            continue
        if f['kind']=='spall':
            rng=np.random.default_rng(7230+index)
            corners=[math.atan2(sy*height,sx*width)%math.tau for sx,sy in ((1,1),(-1,1),(-1,-1),(1,-1))]
            angles=sorted(set(list(np.linspace(0,math.tau,40,endpoint=False))+corners))
            outer=[];inner=[];bottom=[]
            for theta in angles:
                d=np.array((math.cos(theta),math.sin(theta),0.))
                t=min(width/2/max(abs(d[0]),1e-9),height/2/max(abs(d[1]),1e-9))
                outer.append(center+d*t)
                ellipse=1/math.sqrt((d[0]/(width*.34))**2+(d[1]/(height*.34))**2)
                radius=ellipse*(1+.043*math.sin(theta*7+index)+.024*math.sin(theta*13))
                inner.append(center+d*radius)
                q=center+d*radius*.958;q[2]-=.68;bottom.append(q)
            mid=center-UP*.68
            for i in range(len(angles)):
                j=(i+1)%len(angles)
                floor_face(model,'cf_floor',[outer[i],outer[j],inner[j],inner[i]])
                B.card(model,'cc_raw',[inner[i],inner[j],bottom[j]],UP)
                B.card(model,'cc_raw',[inner[i],bottom[j],bottom[i]],UP)
                B.card(model,'cc_raw',[bottom[i],bottom[j],mid],UP)
            for _ in range(15):
                theta=float(rng.uniform(0,math.tau));r=math.sqrt(float(rng.uniform(.02,.68)))
                p=center+np.array((math.cos(theta)*width*.29*r,math.sin(theta)*height*.29*r,-.68))
                size=float(rng.uniform(.24,.72))
                B.lathe(model,p,UP,[(size*.7,0),(size,.05),(size*.55,.18),(size*.25,.24)],
                    'cc_raw',sides=5,cap='cc_raw',turn=theta)
            continue
        # Cut slab reveals, a dark pocket, and a flush metal support frame.
        bevel_box(model,center-UP*1.3,np.eye(3),(width,height,.4),'cc_seal',.1)
        for a,b in (((x0,y0,z),(x1,y0,z)),((x1,y0,z),(x1,y1,z)),
                    ((x1,y1,z),(x0,y1,z)),((x0,y1,z),(x0,y0,z))):
            a,b=np.array(a),np.array(b)
            B.card(model,'cc_raw',[a,b,b-UP*1.4,a-UP*1.4],np.cross(b-a,-UP))
        rim=.7
        for lo,hi in (((x0,y0,z-.42),(x1,y0+rim,z-.03)),((x0,y1-rim,z-.42),(x1,y1,z-.03)),
                      ((x0,y0+rim,z-.42),(x0+rim,y1-rim,z-.03)),((x1-rim,y0+rim,z-.42),(x1,y1-rim,z-.03))):
            F.block(model,lo,hi,'cc_metal',.10)
        if f['kind']=='grate':
            for y in np.arange(y0+1.45,y1-1.0,1.75):
                F.block(model,(x0+.85,y-.18,z-.6),(x1-.85,y+.18,z-.06),'cc_metal',.08)
            for x in (x0+3,x1-3):
                F.block(model,(x-.15,y0+.8,z-.86),(x+.15,y1-.8,z-.55),'cc_rail',.06)
        else:
            F.block(model,(x0+1,y0+1,z-.8),(x1-1,y1-1,z-.12),'cc_rail',.25)
            # Actual recessed joint between two service-cover leaves.
            handles=[]
            for xx0,xx1 in ((x0+1.2,center[0]-.12),(center[0]+.12,x1-1.2)):
                handle=np.array(((xx0+xx1)/2,y0+13,z))
                handles.append(handle)
                cover=K.Model()
                F.block(cover,(xx0,y0+1.2,z-.35),(xx1,y1-1.2,z-.02),'cc_rail',.13)
                slot=dict(rect=(handle[0]-2,handle[0]+2,handle[1]-1.65,handle[1]+1.65),z=z-.02)
                for paint,polys in cover.polygons.items():
                    for points,normal in polys:
                        if normal[2]>.99:
                            uv=[K.face_uv(K.to_world(p),UP,paint,K.uv_offset('collider_structure'),64.) for p in points]
                            pieces,changed=cut_floor(points,uv,(slot,))
                            if changed:
                                for polygon in pieces:model.polygon(paint,[v[:3] for v in polygon],normal,uv=[v[3:] for v in polygon])
                                continue
                        model.polygon(paint,points,normal)
                sx0,sx1,sy0,sy1=slot['rect']
                B.card(model,'cc_seal',[(sx0,sy0,z-.3),(sx1,sy0,z-.3),(sx1,sy1,z-.3),(sx0,sy1,z-.3)],UP)
                for a,b in (((sx0,sy0,z-.02),(sx1,sy0,z-.02)),((sx1,sy0,z-.02),(sx1,sy1,z-.02)),
                            ((sx1,sy1,z-.02),(sx0,sy1,z-.02)),((sx0,sy1,z-.02),(sx0,sy0,z-.02))):
                    a,b=np.array(a),np.array(b)
                    B.card(model,'cc_rail',[a,b,b-UP*.28,a-UP*.28],np.cross(b-a,-UP))
                profile=[(1.12+.12*math.cos(a),.12*math.sin(a)) for a in np.linspace(0,math.tau,9)]
                B.lathe(model,handle-UP*.17,UP,profile,'cc_metal',sides=20)
                F.block(model,(handle[0]-.65,handle[1]+.94,z-.27),(handle[0]+.65,handle[1]+1.35,z-.07),'cc_metal',.06)
            for x in (x0+3,x1-3):
                for y in (y0+3,y1-3):F.fastener(model,(x,y,z-.01),UP,.25)


def refine_floor(model):
    result=K.Model()
    for paint,polys in model.polygons.items():
        for i,(points,normal) in enumerate(polys):
            uv=model.polygon_uvs.get((paint,i))
            if paint=='cf_floor' and normal[2]>.99:
                fragments,changed=cut_floor(points,uv or [floor_uv(p) for p in points])
                if changed:
                    for polygon in fragments:
                        result.polygon(paint,[v[:3] for v in polygon],UP,uv=[v[3:] for v in polygon])
                    continue
            result.polygon(paint,points,normal,uv=uv,normals=model.polygon_normals.get((paint,i)))
    model.polygons=result.polygons;model.polygon_uvs=result.polygon_uvs;model.polygon_normals=result.polygon_normals
    floor_details(model);configure(model)


def materials(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    n,m=1024,512;rng=np.random.default_rng(284731)
    grain=rng.standard_normal((m,n)).astype(np.float32)
    x=np.arange(n)[None,:]/n;y=np.arange(m)[:,None]/m
    # Tool-authored coating maps: hand contact follows the top of the circular
    # tube in its cylindrical UVs instead of painting wear over every surface.
    noise=np.asarray(Image.fromarray(np.uint8(rng.random((64,128))*255)).resize((n,m),Image.Resampling.BICUBIC),float)/255
    # OBJ V is bottom-up; the tube's +up circumference (V=.25) samples
    # row .75 in a PNG. Keep contact wear on the actual upper surface.
    top=np.exp(-((y-.75)/.055)**2)
    contact=top*np.clip((noise-.43)*3.8,0,1)
    scratches=Image.new('L',(n,m));draw=ImageDraw.Draw(scratches)
    for i in range(180):
        xx=int(rng.integers(0,n));yy=int(rng.normal(m*.75,m*.034));length=int(rng.integers(3,35))
        draw.line((xx,yy,xx+length,yy+int(rng.integers(-2,3))),fill=int(rng.integers(65,240)),width=1)
    scratch=np.asarray(scratches,float)/255
    chips=np.clip((contact-.68)*4,0,1)
    for name,wear in [('rail',False),('hand',True)]:
        color=np.array((48.,57.,59.))[None,None,:]+grain[...,None]*.7
        rough=np.clip(.66+grain*.012+(noise-.5)*.035,0,1)
        metal=np.full((m,n),.015)
        height=grain*.0005
        if wear:
            bare=np.clip(chips+scratch*.7,0,1)
            color=color*(1-bare[...,None])+np.array((112.,119.,119.))[None,None,:]*bare[...,None]
            rough=np.clip(rough-contact*.19-bare*.12,.24,.75)
            metal=metal*(1-bare)+bare*.92
            height=height-bare*.025
        dy,dx=np.gradient(height)
        normal=np.dstack((-dx*12,dy*12,np.ones((m,n))))
        normal/=np.linalg.norm(normal,axis=2,keepdims=True)
        Image.fromarray(np.uint8(np.clip(color,0,255))).save(out/f'{name}_color.png')
        Image.fromarray(np.uint8(rough*255)).save(out/f'{name}_rough.png')
        Image.fromarray(np.uint8(metal*255)).save(out/f'{name}_metal.png')
        Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/f'{name}_normal.png')
        text=F.vmat(f'{MATERIAL_DIR}/{name}_color.png',f'{MATERIAL_DIR}/{name}_normal.png',f'{MATERIAL_DIR}/{name}_rough.png')
        text=text.replace('g_flMetalness "0.0"',f'TextureMetalness "{MATERIAL_DIR}/{name}_metal.png"')
        (out/f'cc_{name}.vmat').write_text(text,encoding='utf-8')
    (out/'cc_metal.vmat').write_text(F.vmat('[0.31 0.34 0.35 1]',
        'materials/railhead/rw_galvanised_normal.png','materials/railhead/rw_galvanised_rough.png',metalness=.82),encoding='utf-8')
    (out/'cc_seal.vmat').write_text(F.vmat('[0.019 0.021 0.020 1]',rough_value=.96),encoding='utf-8')
    (out/'cc_raw.vmat').write_text(F.vmat('materials/collider/finish-v1/hangar_concrete_floor_diff_2k.jpg',
        'materials/collider/finish-v1/hangar_concrete_floor_nor_gl_2k.png',rough_value=.98,
        tint=(1.22,1.28,1.30),scale=64/(2000/25.4)),encoding='utf-8')
