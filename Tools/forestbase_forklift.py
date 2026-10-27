"""Reference industrial forklift, authored at the existing loading-yard footprint.
Static prop: no runtime scripts, extra lights or animated beacons. Original body
and four tire proxies are retained. All dimensions are plan inches.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import map_kit as K

RES='materials/forestbase/forklift'

def build(m,api):
    m.collision_box((-52,-28,18),(52,28,46),'metal')
    wheels=api['model'](not isinstance(m,api['CollisionOnlyModel']))
    for x in (-32,35):
        for y in (-30,30):api['wheel'](wheels,x,y,15,15,9)
    m.hulls.extend(wheels.hulls)
    if isinstance(m,api['CollisionOnlyModel']):return
    for p in ('paint','metal','vent','tread','labels','headlamp','amber','tail'):
        m.material_overrides['forklift_'+p]=f'{RES}/{p}.vmat';m.tile_overrides['forklift_'+p]=64
    for p,faces in wheels.polygons.items():
        target={'rubber':'vehicle_rubber','steel':'forklift_metal'}.get(p,p)
        for i,(pts,norm) in enumerate(faces):
            m.polygon(target,pts,normal=norm,uv=wheels.polygon_uvs.get((p,i)),normals=wheels.polygon_normals.get((p,i)))
    bevel=api['bevel_box'];box=api['box'];tube=api['tube'];metal='forklift_metal';rubber='vehicle_rubber'
    def block(a,b,p='forklift_paint',r=.6):
        if p not in ('forklift_paint','forklift_metal'):
            bevel(m,a,b,p,r);return
        temp=K.Model();bevel(temp,a,b,p,r)
        for pts,norm in temp.polygons[p]:
            axis=int(np.argmax(abs(norm)));axes=(1,2) if axis==0 else (0,2) if axis==1 else (0,1)
            uv=[((q[axes[0]]-a[axes[0]])/(b[axes[0]]-a[axes[0]]),
                 (q[axes[1]]-a[axes[1]])/(b[axes[1]]-a[axes[1]])) for q in pts]
            m.polygon(p,pts,normal=norm,uv=uv)
    def panel(pts,p):m.polygon(p,pts,uv=((0,0),(1,0),(1,1),(0,1)))
    def cushion(a,b,r,recline=0):
        # Smooth rounded upholstery, including its corner normals. A shear
        # reclines the backrest; it is not an upright rectangular seat block.
        center=(np.array(a)+b)/2;half=(np.array(b)-a)/2
        inner=half-min(r,float(min(half))*.95)
        radius=min(r,float(min(half))*.95)
        for axis in range(3):
            others=[q for q in range(3) if q!=axis]
            def point(u,v,sign):
                q=np.zeros(3);q[axis]=half[axis]*sign;q[others]=[u*half[others[0]],v*half[others[1]]]
                nearest=np.clip(q,-inner,inner);normal=K.normalise(q-nearest)
                p=center+nearest+normal*radius;p[0]-=recline*(p[2]-a[2])
                normal[2]+=recline*normal[0]
                return p,K.normalise(normal)
            for sign in (-1,1):
                for u in np.linspace(-1,1,7)[:-1]:
                    for v in np.linspace(-1,1,7)[:-1]:
                        data=[point(u,v,sign),point(u+1/3,v,sign),point(u+1/3,v+1/3,sign),point(u,v+1/3,sign)]
                        pts=[q[0] for q in data];normals=[q[1] for q in data]
                        if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),np.mean(normals,axis=0))<0:pts.reverse();normals.reverse()
                        m.polygon(rubber,pts,normals=normals)
    def bolt(x,y,z,axis=(0,0,1),r=.55):
        a=np.array((x,y,z));axis=np.array(axis);tube(m,a,a+axis*.38,r,metal,segments=6)
    # Inboard chassis and rounded rear counterweight. Outboard skins have
    # actual wheel cutouts, leaving the profiled tires visible in silhouette.
    block((-52,-22,18),(52,22,46),r=2.3)
    block((-53,-28,18),(-50,28,51),r=1.5)
    block((-52,-28,35),(-26,28,53),r=2)
    block((-49,-25,52),(-26,25,54),r=.8)
    for side in (-1,1):
        y=side*28
        xs=sorted(set([-52,52,-17,20]+[float(x+c) for c in (-32,35) for x in np.linspace(-17,17,17)]))
        xs=[x for x in xs if -52<=x<=52]
        for a,b in zip(xs,xs[1:]):
            def lower(x):
                return max([18]+[15+math.sqrt(max(0,17**2-(x-c)**2)) for c in (-32,35) if abs(x-c)<17])
            za,zb=lower(a),lower(b)
            q=[(a,y,za),(b,y,zb),(b,y,46),(a,y,46)]
            uv=[((x+52)/104,(zz-18)/28) for x,_,zz in q]
            if side>0:q.reverse();uv.reverse()
            m.polygon('forklift_paint',q,uv=uv)
            # A dark flange gives the arch its sheet-metal thickness.
            q=[(a,y,za),(a,y-side*5,za),(b,y-side*5,zb),(b,y,zb)]
            if side>0:q.reverse()
            m.polygon(metal,q)
        # Separate removable service panel, seam, latches and recessed vent.
        block((-13,y-side*.1,33),(17,y+side*.28,45),'forklift_paint',.25) if side>0 else block((-13,y+side*.28,33),(17,y-side*.1,45),'forklift_paint',.25)
        yy=y+side*.35
        pts=[(-10,yy,35),(14,yy,35),(14,yy,43),(-10,yy,43)]
        if side>0:pts.reverse()
        panel(pts,'forklift_vent')
        # Painted diagonal safety stripes between the wheel arches.
        for x in (-11,0,11):
            pts=[(x-3,y+side*.22,21),(x+2,y+side*.22,21),(x+10,y+side*.22,30),(x+5,y+side*.22,30)]
            if side>0:pts.reverse()
            m.polygon(metal,pts)
        for x in (-48,-21,20,48):
            for zz in (34,44):bolt(x,y+side*.5,zz,(0,side,0))
        # Driver access step, anti-slip deck and compact ignition panel.
        block((17,min(y,y+side*4),31),(43,max(y,y+side*4),34),metal,.5)
        block((33,min(y,y+side*.7),37),(45,max(y,y+side*.7),45),metal,.5)
        tube(m,(37,y+side,41),(37,y+side*1.8,41),1,metal,12)
        pts=[(21,y+side*.82,34),(30,y+side*.82,34),(30,y+side*.82,43),(21,y+side*.82,43)]
        if side>0:pts.reverse()
        panel(pts,'forklift_labels')
    # Rear cooling grille, tow socket and paired protected tail lamps.
    block((-53,-20,26),(-52.1,20,43),metal,.5)
    panel([(-53.12,17,28),(-53.12,-17,28),(-53.12,-17,41),(-53.12,17,41)],'forklift_vent')
    block((-54,-7,19),(-52,7,25),metal,.6)
    for y in (-20,20):
        block((-53.8,y-2.6,38),(-52.5,y+2.6,49),metal,.5)
        block((-54.05,y-1.9,42),(-53.85,y+1.9,48),'forklift_tail',.2)
        block((-54.05,y-1.9,39),(-53.85,y+1.9,42),'forklift_amber',.15)
    # Floor pan, seat slides, stitched cushions and correctly forward-facing back.
    block((-25,-24,46),(43,24,49),metal,.7)
    panel([(-23,-22,49.15),(40,-22,49.15),(40,22,49.15),(-23,22,49.15)],'forklift_tread')
    for y in (-10,10):block((-25,y-1.3,49),(10,y+1.3,52),metal,.4)
    cushion((-25,-17,52),(10,17,59),3.1)
    cushion((-23,-15,57.5),(8,15,60.7),1.3)
    cushion((-33,-17,57),(-23,17,92),4,.08)
    cushion((-24,-14,63),(-20.5,14,89),1.6,.08)
    cushion((-21.3,-10,60),(-18.5,10,71),1.3,.08)
    for y in (-18,18):
        tube(m,(-25,y,54),(-25,y,67),.8,metal,10)
        tube(m,(-25,y,67),(-10,y,67),.8,metal,10)
    # Sloped steering column, toroidal wheel with three spokes, and levers.
    block((20,-8,49),(37,8,55),metal,1)
    center=np.array((19,0,78));axis=K.normalise(center-np.array((30,0,51)))
    tube(m,(30,0,51),center,2.5,metal,16)
    u=np.array((0,1,0));v=np.cross(axis,u)
    for a,b in zip(np.linspace(0,math.tau,41)[:-1],np.linspace(0,math.tau,41)[1:]):
        tube(m,center+9.4*(u*math.cos(a)+v*math.sin(a)),center+9.4*(u*math.cos(b)+v*math.sin(b)),.9,rubber,8)
    tube(m,center-axis,center+axis,2.5,metal,16)
    for a in (0,math.tau/3,math.tau*2/3):tube(m,center,center+8.7*(u*math.cos(a)+v*math.sin(a)),.65,metal,8)
    for j in range(2):
        tube(m,(31+j*4,-16,50),(28+j*4,-16,73-j*3),.55,metal,8)
        block((26.5+j*4,-17.5,71.5-j*3),(29.5+j*4,-14.5,75-j*3),rubber,1.2)
    # Protective overhead cage with bolted feet, yellow roof and carry loops.
    for x in (-33,32):
        for y in (-24,24):
            block((x-3.5,y-3.5,48),(x+3.5,y+3.5,49.3),metal,.35)
            block((x-1.7,y-1.7,49),(x+1.7,y+1.7,115),metal,.3)
            for yy in (-2.5,2.5):bolt(x,y+yy,49.4)
    block((-39,-30,114),(41,30,120),r=1.2)
    for x in (-29,30):
        for a,b in [((x,-21,120),(x,-21,123)),((x,-21,123),(x,-15,123)),((x,-15,123),(x,-15,120))]:tube(m,a,b,.55,metal,10)
    # Static LED work lights. No point lights or blinking state.
    for y in (-25,25):
        block((-43,y-4,111),(-38,y+4,119),metal,1)
        block((-43.4,y-3.1,111.9),(-43.05,y+3.1,118.1),rubber,.4)
        for row in range(4):
            for col in range(4):block((-43.7,y-2.6+col*1.4,112.4+row*1.4),(-43.5,y-1.5+col*1.4,113.5+row*1.4),'forklift_headlamp',.12)
    tube(m,(-3,0,120),(-3,0,121),3.4,metal,20)
    tube(m,(-3,0,121),(-3,0,126),2.6,'forklift_amber',24)
    tube(m,(-3,0,126),(-3,0,126.6),2.9,metal,24)
    for a in np.linspace(0,math.tau,8,endpoint=False):
        x=-3+3.1*math.cos(a);y=3.1*math.sin(a);tube(m,(x,y,120.8),(x,y,127),.16,metal,6)
    # Open C-channel mast, inner sliders, lift chains, hydraulic ram, carriage.
    for y in (-26,26):
        for yy in (y-3,y+3):block((50,yy-.55,9),(56,yy+.55,142),metal,.3)
        block((55,y-3,9),(56,y+3,142),metal,.3)
        block((51,y-1.1,12),(53.5,y+1.1,136),metal,.2)
        for zz in np.arange(19,133,3):
            block((49.7,y-.65,zz),(50.5,y+.65,zz+2),metal,.15)
        for zz in (15,132):
            block((49,y-4,zz),(57,y+4,zz+4),metal,.4)
            for yy in (y-2.5,y+2.5):bolt(48.8,yy,zz+2,(-1,0,0))
    block((50,-29,135),(57,29,140),metal,.5)
    block((51,-24,13),(57,24,17),metal,.5)
    tube(m,(53,0,18),(53,0,85),2.1,metal,16)
    tube(m,(53,0,80),(53,0,124),1.2,metal,16)
    for zz in (18,35):block((56,-24,zz),(60,24,zz+4),metal,.4)
    for y in (-20,20):
        block((57,y-3,12),(61,y+3,38),metal,.45)
        # Tapered fork tip: low wedge rather than a blunt rectangular block.
        p=[(60,y-3,12),(109,y-3,12),(109,y-3,13),(92,y-3,16),(60,y-3,16)]
        q=[(x,y+3,z) for x,_,z in p]
        m.polygon(metal,p);m.polygon(metal,list(reversed(q)))
        for k in range(5):m.polygon(metal,[p[k],q[k],q[(k+1)%5],p[(k+1)%5]])

def materials(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(51227);n=1024
    noise=rng.normal(0,1.7,(n,n));cloud=np.asarray(Image.fromarray(rng.integers(70,180,(32,32),dtype=np.uint8)).resize((n,n),Image.Resampling.BICUBIC),float)-127
    col=np.clip(np.array((174,126,37))+noise[:,:,None]+cloud[:,:,None]*.1,0,255).astype('uint8')
    paint=Image.fromarray(col);d=ImageDraw.Draw(paint)
    for k in range(4200):
        side=int(rng.integers(4));p=float(rng.uniform(0,n));depth=float(rng.exponential(8)+3)
        x,y=(p,depth) if side==0 else (p,n-depth) if side==1 else (depth,p) if side==2 else (n-depth,p)
        dx,dy=(float(rng.uniform(1,20)),float(rng.uniform(1,4))) if side<2 else (float(rng.uniform(1,4)),float(rng.uniform(1,20)))
        d.rectangle((x,y,x+dx,y+dy),fill=(59,59,49) if k%4 else (122,119,99))
    for k in range(1100):
        x,y=rng.integers(20,n-20,2);d.line((int(x),int(y),int(x+rng.integers(1,13)),int(y+1)),fill=(92,79,48) if k%3 else (62,61,50),width=int(rng.integers(1,3)))
    for k in range(380):
        x,y=rng.integers(18,n-18,2);radius=float(rng.uniform(2,6))
        pts=[(x+math.cos(a)*radius*rng.uniform(.5,1.4),y+math.sin(a)*radius*rng.uniform(.5,1.4)) for a in np.linspace(0,math.tau,7,endpoint=False)]
        d.polygon(pts,fill=(70,65,47) if k%3 else (106,101,80))
    # Worn graphite steel, with wear concentrated at the edge of each part.
    gray=np.clip(131-np.asarray(paint).mean(axis=2)*.78,25,130)
    steel=Image.fromarray(np.stack((gray,gray*1.02,gray*.97),axis=-1).astype('uint8'))
    vent=Image.new('RGB',(512,512),(25,27,24));vd=ImageDraw.Draw(vent)
    for row,y in enumerate(range(-12,540,24)):
        for x in range(-20,540,28):
            cx=x+(14 if row%2 else 0);pts=[(cx+13*math.cos(a),y+13*math.sin(a)) for a in np.linspace(0,math.tau,7)];vd.line(pts,fill=(65,67,60),width=3)
    tread=Image.new('RGB',(512,512),(50,52,48));td=ImageDraw.Draw(tread)
    for row,y in enumerate(range(0,512,48)):
        for x in range(0,512,48):
            a=x+(24 if row%2 else 0);td.line((a,y,a+15,y+12),fill=(101,102,91),width=4);td.line((a+1,y+3,a+14,y+14),fill=(25,28,25),width=2)
    label=Image.new('RGB',(512,512),(181,144,63));ld=ImageDraw.Draw(label);font=lambda s:ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',s)
    ld.rectangle((12,12,499,499),outline=(51,48,35),width=10);ld.polygon([(255,48),(422,315),(88,315)],outline=(40,40,31),width=15)
    ld.text((225,115),'!',font=font(150),fill=(40,40,31));ld.text((78,335),'CAUTION',font=font(75),fill=(40,40,31));ld.text((67,433),'CAPACITY 2000 KG',font=font(36),fill=(40,40,31))
    for name,im,rough,metal in [('paint',paint,.76,.08),('metal',steel,.62,.72),('vent',vent,.68,.55),('tread',tread,.65,.62),('labels',label,.82,0)]:
        im.save(out/(name+'_color.png'),compress_level=4)
        arr=np.asarray(im).mean(axis=2);height=(arr-arr.mean())*.0003
        dy,dx=np.gradient(height);normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
        Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(out/(name+'_normal.png'),compress_level=4)
        (out/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/forestbase_coating.shader"\n F_SPECULAR "1"\n'+f' TextureColor "{RES}/{name}_color.png"\n TextureNormal "{RES}/{name}_normal.png"\n TextureRoughness "[{rough} {rough} {rough} 0]"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_flCoatingMetalness "{metal}"\n g_flModelTintAmount "1"\n}}\n')
    for name,c,bright in [('headlamp','0.92 0.96 1',1.5),('amber','1 0.55 0.08',.65),('tail','0.22 0.012 0.006',0)]:
        (out/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n'+f' F_SELF_ILLUM "1"\n TextureSelfIllumMask "[1 1 1 0]"\n g_flSelfIllumBrightness "{bright}"\n g_flSelfIllumAlbedoFactor "1"\n g_vSelfIllumTint "[{c} 0]"\n TextureColor "[{c} 0]"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[.7 .7 .7 0]"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_flModelTintAmount "1"\n}}\n')
