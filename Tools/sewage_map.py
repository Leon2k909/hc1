"""Sewage: the reference-image waterworks, staged for import through the live editor.

Run: rtk python Tools/sewage_map.py
Never writes scene/resources to Assets: Sources/Sewage/editor imports the staged
assets and scene through s&box. Coordinates use map_kit's east/north/up convention.
"""
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/sewage/stage'
MAT = STAGE / 'materials/sewage'
MOD = STAGE / 'models/maps/sewage'
RNG = np.random.default_rng(15026)
IDS = K.SceneIds('d6ab2592-265b-48f5-8afe-97c5206e0c43')
PAINTS = {}
LIGHTS = []

def noise(shape, scale, rng=RNG):
    small = rng.random((max(2, int(shape[0]/scale)), max(2, int(shape[1]/scale)))).astype(np.float32)
    return np.asarray(Image.fromarray(small, mode='F').resize((shape[1], shape[0]), Image.Resampling.BICUBIC))

def texture(name, base, kind='concrete', tile=192, metal=0):
    n=1024; shape=(n,n); yy,xx=np.mgrid[:n,:n]
    fine=noise(shape,2); med=noise(shape,18); broad=noise(shape,140)
    grain=.48*fine+.30*med+.22*broad
    color=np.ones((n,n,3))*np.array(base)[None,None,:]
    color*=.66+.68*grain[...,None]
    height=.16*fine+.12*med
    rough=np.full(shape,.8)
    if kind in ('concrete','brick'):
        streak=noise((n,n),45)*noise((n,64),18).repeat(16,axis=1)
        moss=np.clip((broad-.5)*4 + (streak-.3)*1.1,0,.85)
        color=color*(1-moss[...,None]*.64)+np.array([23,34,16])*moss[...,None]*.45
        drip=np.clip((noise((128,n),9).repeat(8,axis=0)-.48)*3,0,1)*(.3+.7*broad)
        color*=1-drip[...,None]*.48
        if kind=='brick':
            rows=yy//64; mortar=((yy%64)<5)|(((xx+(rows%2)*96)%192)<5)
            height+=np.where(mortar,-.3,.15)
            color[mortar]*=.32
        else:
            seam=((xx%512)<3)|((yy%512)<3)
            color[seam]*=.45; height[seam]-=.12
            for x,y in [(28,28),(484,28),(28,484),(484,484),(540,540),(996,996)]:
                hole=(xx-x)**2+(yy-y)**2<28
                color[hole]*=.4; height[hole]-=.1
        rough=.5+.4*grain
    elif kind in ('steel','yellow','rust'):
        corrode=np.clip((med*.6+broad*.4-.44)*4,0,1)
        rust=np.stack([81+grain*40,38+grain*24,16+grain*12],axis=-1)
        color=color*(1-corrode[...,None])+rust*corrode[...,None]
        height+=corrode*.16
        rough=.33+.54*corrode
        scratches=(noise((n,n),3)>.78)&(noise((n,64),3).repeat(16,axis=1)>.5)
        color[scratches]*=.52
    elif kind=='floor':
        cracks=((xx%256)<4)|((yy%256)<4)
        color[cracks]*=.28; height[cracks]-=.25
        puddle=np.clip((broad-.48)*6,0,1)
        color*=1-puddle[...,None]*.38
        rough=.16+.7*(1-puddle)
    elif kind=='grate':
        bar=((xx%48)<9)|((yy%48)<8)
        color[~bar]=np.array([5,8,6]); height+=bar*.34
        rough=.43+.25*grain
    gy,gx=np.gradient(height)
    norm=np.stack([-gx*4,gy*4,np.ones(shape)],axis=-1)
    norm/=np.linalg.norm(norm,axis=-1)[...,None]
    MAT.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.clip(color,0,255).astype('uint8')).save(MAT/f'{name}_color.png')
    Image.fromarray(np.clip((norm*.5+.5)*255,0,255).astype('uint8')).save(MAT/f'{name}_normal.png')
    Image.fromarray(np.clip(rough*255,0,255).astype('uint8')).save(MAT/f'{name}_rough.png')
    material(name,metal=metal)
    PAINTS[name]=tile

def material(name,metal=0,emission=None):
    text=f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "{metal}"
    TextureColor "materials/sewage/{name}_color.png"
    TextureNormal "materials/sewage/{name}_normal.png"
    TextureRoughness "materials/sewage/{name}_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
'''
    if emission:
        text+=f'    F_SELF_ILLUM "1"\n    g_vSelfIllumTint "[{emission}]"\n    g_flSelfIllumBrightness "3"\n    TextureSelfIllumMask "materials/default/default_ao.tga"\n'
    K.write_text(MAT/f'{name}.vmat',text+'}\n')

def sign(name,lines,size=(768,1024),red=False,symbol=False):
    w,h=size
    substrate=Image.open(MAT/'concrete_color.png').resize(size)
    pixels=np.asarray(substrate).astype(float)*.72
    im=Image.fromarray(np.uint8(pixels)); layer=Image.new('RGBA',size); d=ImageDraw.Draw(layer)
    top=int(h*.08)
    if symbol:
        cx=w//2; cy=int(h*.24); r=int(w*.30)
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(187,190,165,210))
        d.polygon([(cx,cy-r*.85),(cx-r*.8,cy+r*.55),(cx+r*.8,cy+r*.55)],fill=(39,48,40,240))
        d.rectangle((cx-8,cy-r*.42,cx+8,cy+r*.1),fill=(190,193,160,230))
        d.ellipse((cx-8,cy+r*.23,cx+8,cy+r*.39),fill=(190,193,160,230))
        top=int(h*.47)
    avail=h-top-int(h*.08)
    for k,line in enumerate(lines):
        fs=min(int(avail/len(lines)*.74),int(w/(max(1,len(line))*.55)))
        font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',fs)
        bbox=d.textbbox((0,0),line,font=font)
        x=(w-(bbox[2]-bbox[0]))//2
        color=(122,31,20,235) if red else (196,195,163,225)
        d.text((x,top+k*avail/len(lines)),line,font=font,fill=color)
    a=np.asarray(layer).copy()
    wear=noise((h,w),5)*.5+noise((h,w),40)*.5
    a[:,:,3]=(a[:,:,3]*(np.clip((wear-.27)*3,0,1))).astype(np.uint8)
    im=Image.alpha_composite(im.convert('RGBA'),Image.fromarray(a)).convert('RGB')
    gpu_size=tuple(2**math.ceil(math.log2(x)) for x in size)
    im.resize(gpu_size,Image.Resampling.LANCZOS).save(MAT/f'{name}_color.png')
    Image.new('RGB',gpu_size,(128,128,255)).save(MAT/f'{name}_normal.png')
    Image.new('L',gpu_size,188).save(MAT/f'{name}_rough.png')
    material(name); PAINTS[name]=256

def materials():
    texture('concrete',(109,112,96),tile=256)
    texture('brick',(81,91,67),'brick',tile=192)
    texture('floor',(80,85,70),'floor',tile=192)
    texture('steel',(57,64,53),'steel',tile=96,metal=.65)
    texture('yellow',(181,130,39),'yellow',tile=64,metal=.4)
    texture('rust',(108,61,29),'rust',tile=96,metal=.35)
    texture('grate',(85,91,77),'grate',tile=96,metal=.55)
    for name,color in [('lamp_amber',(255,219,139)),('lamp_white',(195,232,222)),('lamp_red',(245,35,13)),('lamp_green',(81,220,137))]:
        Image.new('RGB',(32,32),color).save(MAT/f'{name}_color.png')
        Image.new('RGB',(32,32),(128,128,255)).save(MAT/f'{name}_normal.png')
        Image.new('L',(32,32),100).save(MAT/f'{name}_rough.png')
        material(name,emission='1 1 1'); PAINTS[name]=64
    sign('tower_sign',['RAVENHOLM','WATERWORKS','','OUR WASTE','THEIR FUTURE'],symbol=True)
    sign('cleaner',['CLEANER','TOMORROW','','A BRIGHTER','HUMANITY'])
    sign('progress',['WASTE','FEEDS','PROGRESS'],size=(512,768))
    sign('purify',['PURIFY','PRESERVE','PROTECT'],size=(512,768))
    sign('warning',['WATCH','YOUR STEP'],size=(768,512))
    sign('gate',['GATE A'],size=(1024,256))
    sign('flow',['FLOW CONTROL','B'],size=(1024,384))
    sign('sector',['SECTOR C','C'],size=(512,512))
    sign('number',['03'],size=(512,512))
    sign('buried',['SOME','THINGS','SHOULD','STAY BURIED'],red=True,size=(512,768))
    sign('still',['STILL','FLOWS'],red=True,size=(512,512))
    sign('direction',['PUMP STATION  ^','FILTRATION  >','< MAINTENANCE'],size=(1024,600))
    K.write_text(MAT/'water.vmat','''"Layer0"
{
 shader "shaders/hc1_lowtide_water.shader"
 g_vWaterColor "[0.025 0.067 0.037]"
 g_vWaterFlow "[-5.2 1.1]"
 g_flRippleTile "34"
 g_flRippleStrength "1.1"
 g_flWaterRoughness "0.13"
 g_flAbsorptionDistance "13"
 g_flBankFade "0.3"
}
'''); PAINTS['water']=128
    K.write_text(MAT/'fall.vmat','''"Layer0"
{
 shader "shaders/sewage_flow.shader"
 g_vFlowTint "[0.32 0.49 0.39]"
 g_flFlowSpeed "1.6"
}
'''); PAINTS['fall']=128
    K.write_text(MAT/'foam.vmat','''"Layer0"
{
 shader "shaders/sewage_flow.shader"
 g_vFlowTint "[0.30 0.47 0.37]"
 g_flFlowSpeed "0.15"
}
'''); PAINTS['foam']=128

def model():
    m=K.Model()
    m.material_overrides.update({k:f'materials/sewage/{k}.vmat' for k in PAINTS})
    m.tile_overrides.update(PAINTS)
    return m

def tube(m,a,b,r,paint='steel',sides=16,cap=True):
    a=np.array(a,float); b=np.array(b,float); direction=K.normalise(b-a)
    u=K.normalise(np.cross(direction, (0,0,1) if abs(direction[2])<.96 else (0,1,0)))
    v=np.cross(direction,u)
    ring=[u*math.cos(t)+v*math.sin(t) for t in np.linspace(0,2*math.pi,sides,endpoint=False)]
    for k in range(sides):
        j=(k+1)%sides; nr=[ring[k],ring[j],ring[j],ring[k]]
        m.polygon(paint,[a+ring[k]*r,a+ring[j]*r,b+ring[j]*r,b+ring[k]*r],normals=nr)
    if cap:
        m.polygon(paint,[a+x*r for x in ring[::-1]])
        m.polygon(paint,[b+x*r for x in ring])

def swept_pipe(m,points,r,paint,open_end=False):
    points=np.asarray(points,float)
    directions=np.diff(points,axis=0)
    directions/=np.linalg.norm(directions,axis=1)[:,None]
    tangents=[directions[0]]+[K.normalise(a+b) for a,b in zip(directions,directions[1:])]+[directions[-1]]
    u=K.normalise(np.cross(tangents[0],(0,0,1) if abs(tangents[0][2])<.96 else (0,1,0)))
    rings=[]
    for d in tangents:
        u=K.normalise(u-d*np.dot(u,d))
        v=np.cross(d,u)
        rings.append([u*math.cos(t)+v*math.sin(t) for t in np.linspace(0,2*math.pi,24,endpoint=False)])
    for i in range(len(points)-1):
        a,b=points[i:i+2]
        for k in range(24):
            j=(k+1)%24;na,nb=rings[i][k],rings[i][j];nc,nd=rings[i+1][j],rings[i+1][k]
            m.polygon(paint,[a+na*r,a+nb*r,b+nc*r,b+nd*r],normals=[na,nb,nc,nd])
    m.polygon(paint,[points[0]+n*r for n in rings[0][::-1]])
    if not open_end:
        m.polygon(paint,[points[-1]+n*r for n in rings[-1]])
    else:
        p=points[-1];d=tangents[-1]
        for k in range(24):
            j=(k+1)%24;na,nb=rings[-1][k],rings[-1][j]
            m.polygon(paint,[p+na*r,p+nb*r,p+nb*(r-4),p+na*(r-4)],normals=[d]*4)
            m.polygon(paint,[p-d*18+na*(r-4),p+na*(r-4),p+nb*(r-4),p-d*18+nb*(r-4)],normals=[-na,-na,-nb,-nb])

def pipe(m,points,r,paint='steel',bolts=True,open_end=False):
    swept_pipe(m,points,r,paint,open_end)
    for a,b in zip(points,points[1:]):
        a=np.array(a,float);b=np.array(b,float);d=K.normalise(b-a)
        if np.linalg.norm(b-a)<80:continue
        if r>=22:
            # Thick trunks are solid; fine cabling remains render-only.
            direction=K.normalise(b-a)
            if abs(direction[2])>.999:
                pad=np.array((r*.825,r*.825,0))
                m.collision_box(np.minimum(a,b)-pad,np.maximum(a,b)+pad,'metal')
            else:
                m.beam(a,b,(r*1.65,r*1.65),None,'metal',up=(0,0,1))
        count=max(1,int(np.linalg.norm(b-a)/190))
        for t in np.linspace(.12,.88,count):
            p=a+(b-a)*t
            tube(m,p-d*3,p+d*3,r*1.22,'rust',24)
            if bolts:
                u=K.normalise(np.cross(d,(0,0,1) if abs(d[2])<.96 else (0,1,0)));v=np.cross(d,u)
                for th in np.linspace(0,2*math.pi,8,endpoint=False):
                    q=p+(u*math.cos(th)+v*math.sin(th))*r*1.08
                    tube(m,q-d*5,q+d*5,max(1.3,r*.07),'steel',6)

def torus(m,center,axis,r,minor,paint='rust',steps=48):
    center=np.array(center,float);axis=K.normalise(axis)
    u=K.normalise(np.cross(axis,(0,0,1) if abs(axis[2])<.96 else (0,1,0)));v=np.cross(axis,u)
    pts=[center+r*(u*math.cos(t)+v*math.sin(t)) for t in np.linspace(0,2*math.pi,steps+1)]
    for a,b in zip(pts,pts[1:]): tube(m,a,b,minor,paint,8,False)

def rail(m,a,b,z,height=42,collide=True):
    a=np.array([*a,z],float);b=np.array([*b,z],float)
    n=max(1,math.ceil(np.linalg.norm(b-a)/64))
    for t in np.linspace(0,1,n+1):
        p=a+(b-a)*t
        tube(m,p,p+(0,0,height),2.3,'yellow',8)
        m.box(p+(-4,-4,0),p+(4,4,3),'rust')
    for h in [20,height]:tube(m,a+(0,0,h),b+(0,0,h),1.8,'yellow',8)
    m.beam(a+(0,0,4),b+(0,0,4),(2,7),'rust')
    if collide:m.beam(a+(0,0,height*.5),b+(0,0,height*.5),(3,height),None,'metal')

def catwalk(m,lo,hi,z):
    m.box((*lo,z-8),(*hi,z),{'default':'rust','+z':'grate'},'metal')
    # Perimeter channel beams, and visible underside cross bracing.
    for e in [lo[0]+4,hi[0]-4]:m.box((e-4,lo[1],z-14),(e+4,hi[1],z),'steel')
    for n in np.arange(lo[1]+10,hi[1],110):m.box((lo[0],n-3,z-17),(hi[0],n+3,z-8),'steel')

def stairs(m,e0,e1,n0,n1,z0,z1):
    count=math.ceil(abs(z1-z0)/8)
    for i in range(count):
        a=n0+(n1-n0)*i/count;b=n0+(n1-n0)*(i+1)/count
        h=z0+(z1-z0)*(i+1)/count
        m.box((e0,min(a,b),h-4),(e1,max(a,b)+.1,h),{'default':'steel','+z':'grate'})
        m.box((e0,min(a,b),h),(e1,min(a,b)+2,h+.6),'yellow')
    # Smooth walkable collision ramp, both nav and character movement use this.
    pts=[(e0,n0,z0-5),(e1,n0,z0-5),(e0,n1,z1-5),(e1,n1,z1-5),
         (e0,n0,z0),(e1,n0,z0),(e0,n1,z1),(e1,n1,z1)]
    m.hull(pts,'metal')
    for e in [e0+3,e1-3]:
        m.beam((e,n0,z0-8),(e,n1,z1-8),(6,13),'steel')
        for t in np.linspace(0,1,max(2,math.ceil(abs(n1-n0)/60))):
            n=n0+(n1-n0)*t;z=z0+(z1-z0)*t
            tube(m,(e,n,z),(e,n,z+42),2.2,'yellow',8)
        for h in [20,42]:tube(m,(e,n0,z0+h),(e,n1,z1+h),2,'yellow',8)

def signface(m,paint,center,right,up,size):
    c=np.array(center,float);r=np.array(right,float)*size[0]/2;u=np.array(up,float)*size[1]/2
    m.polygon(paint,[c-r-u,c+r-u,c+r+u,c-r+u],uv=[(0,0),(1,0),(1,1),(0,1)],both_sides=True)

def tower_stencil(m,paint,center,radius,z,size):
    # Follow the pump wall so the stencil does not float in front of its curved face.
    width,height=size
    for i in range(24):
        u0=i/24;u1=(i+1)/24
        def p(u,h):
            angle=(u-.5)*width/radius
            return (center[0]+radius*math.sin(angle),center[1]-radius*math.cos(angle),h)
        m.polygon(paint,[p(u0,z-height/2),p(u1,z-height/2),p(u1,z+height/2),p(u0,z+height/2)],
                  uv=[(u0,0),(u1,0),(u1,1),(u0,1)],both_sides=True)

def lamp(m,p,kind='amber',radius=340,power=1,shadow=False):
    p=np.array(p,float)
    m.box(p+(-10,-5,-5),p+(10,5,5),'steel')
    m.box(p+(-8,-6,-3),p+(8,-5.1,3),'lamp_'+kind)
    m.box(p+(-8,-3,-5.7),p+(8,3,-5.1),'lamp_'+kind)
    for e in [-5,0,5]:tube(m,p+(e,-6.5,-4),p+(e,-6.5,4),.5,'steel',5)
    colors={'amber':(1,.64,.26),'white':(.48,.75,.81),'green':(.16,.68,.33),'red':(1,.055,.018)}
    LIGHTS.append((p+np.array((0,-9,-6)),tuple(v*power for v in colors[kind]),radius,shadow))

def arc_tunnel(m,e0,e1,ncenter,r=115,spring=48):
    for e in np.linspace(e0,e1,6):
        for i in range(24):
            a=math.pi*i/24;b=math.pi*(i+1)/24
            pts=[(e-4,ncenter+r*math.cos(a),spring+r*math.sin(a)),(e-4,ncenter+r*math.cos(b),spring+r*math.sin(b)),
                 (e+4,ncenter+r*math.cos(b),spring+r*math.sin(b)),(e+4,ncenter+r*math.cos(a),spring+r*math.sin(a))]
            m.polygon('steel',pts,both_sides=True)
    for i in range(32):
        a=math.pi*i/32;b=math.pi*(i+1)/32
        p=[(e0,ncenter+r*math.cos(a),spring+r*math.sin(a)),(e1,ncenter+r*math.cos(a),spring+r*math.sin(a)),
           (e1,ncenter+r*math.cos(b),spring+r*math.sin(b)),(e0,ncenter+r*math.cos(b),spring+r*math.sin(b))]
        m.polygon('brick',p,both_sides=True)
        # Collision only on arch shell.
        m.hull(p+[(e,n+(n-ncenter)*.10,z+(z-spring)*.10) for e,n,z in p],'default')
    m.box((min(e0,e1),ncenter-r-20,-16),(max(e0,e1),ncenter+r+20,0),'floor','default')
    for n in [ncenter-r,ncenter+r]:m.box((min(e0,e1),n-10,0),(max(e0,e1),n+10,spring),'brick','default')
    # Closed maintenance branches end in heavy grilles.
    end=e1
    m.box((end-10,ncenter-r,-10),(end+10,ncenter+r,170),'concrete','default')
    for n in np.arange(ncenter-r+12,ncenter+r,15):tube(m,(end-12,n,0),(end-12,n,150),2,'steel',8)

def build():
    shell=model(); tower=model(); walks=model(); pipes=model(); detail=model(); signs=model(); water=model(); falls=model()
    # Sunken channel and surrounding ground-floor circulation.
    shell.box((-1000,-980,-172),(1000,1020,-150),'concrete','default')
    for a,b in [((-1000,-980),(-620,1020)),((740,-980),(1000,1020)),((-620,-980),(740,-580)),((-620,780),(740,1020))]:
        shell.box((*a,-150),(*b,0),{'default':'brick','+z':'floor'},'default')
    # Basin intermediate ledges and escape stairs to prevent a player trap.
    stairs(walks,-610,-475,-510,-160,-150,0)
    catwalk(walks,(-660,-160),(-475,-60),0)
    stairs(walks,595,730,380,740,-150,0)
    catwalk(walks,(595,740),(790,800),0)
    # Left/right walls contain actual arch openings; no solid box across a tunnel.
    for e,nc in [(-1000,-230),(1000,80)]:
        a=e-24;b=e+24
        shell.box((a,-980,0),(b,nc-140,1120),'concrete','default')
        shell.box((a,nc+140,0),(b,1020,1120),'concrete','default')
        shell.box((a,nc-140,210),(b,nc+140,1120),'concrete','default')
        for i in range(24):
            t=math.pi*i/24;u=math.pi*(i+1)/24
            p=[(e-29,nc+115*math.cos(t),48+115*math.sin(t)),(e-29,nc+115*math.cos(u),48+115*math.sin(u)),
               (e+29,nc+115*math.cos(u),48+115*math.sin(u)),(e+29,nc+115*math.cos(t),48+115*math.sin(t))]
            outer=[(x,nc+(n-nc)*140/115,48+(z-48)*140/115) for x,n,z in p]
            shell.hull(p+outer,'default')
            shell.polygon('brick',[p[0],p[1],outer[1],outer[0]],both_sides=True)
            shell.polygon('brick',[p[2],p[3],outer[3],outer[2]],both_sides=True)
            shell.polygon('brick',p,both_sides=True)
            # Solid spandrels join the curved masonry to the straight wall above.
            # Without these faces the rectangular opening exposes the outside sky.
            top=[(x,n,210) for x,n,z in outer]
            shell.hull(outer+top,'default')
            shell.polygon('concrete',[outer[0],outer[1],top[1],top[0]],both_sides=True)
            shell.polygon('concrete',[outer[2],outer[3],top[3],top[2]],both_sides=True)
        for side in [-1,1]:
            ns=sorted([nc+side*115,nc+side*140])
            shell.box((a,ns[0],0),(b,ns[1],48),'brick','default')
        arc_tunnel(shell,e,e+(-500 if e<0 else 500),nc)
        for pos in [e+(-140 if e<0 else 140),e+(-380 if e<0 else 380)]:
            lamp(detail,(pos,nc,155),'green' if e<0 else 'red',260,1.9)
    shell.box((-1024,1020,-150),(1024,1050,1140),'concrete','default')
    shell.box((-1024,-1010,-150),(1024,-980,1140),'concrete','default')
    # Steel roof with three skylight wells.
    for e0,e1 in [(-1024,-520),(-400,80),(210,670),(790,1024)]:
        shell.box((e0,-980,1120),(e1,1050,1140),'steel','default')
    for e in [-460,145,730]:
        for a,b in [(-980,200),(310,820),(930,1050)]:shell.box((e-60,a,1120),(e+60,b,1140),'steel')
        for n in [255,875]:
            shell.box((e-60,n-55,1135),(e+60,n+55,1140),'lamp_white')
            for off in [-25,25]:shell.box((e-62,n+off-3,1122),(e+62,n+off+3,1135),'steel')
        LIGHTS.append((np.array((e,220,1020)),(.45,.65,.78),1100,True))
    for n in np.arange(-850,1000,330):
        shell.beam((-1000,n,1040),(1000,n,1040),(16,40),'steel')
        for e in range(-950,1000,250):
            shell.beam((e,n,1040),(e+150,n,1120),(9,9),'rust')
    for e in [-965,965]:
        for n in [-850,-500,150,520,900]:
            shell.box((e-18,n-25,0),(e+18,n+25,1080),'brick','default')
            for z in [260,560,900]:shell.box((e-23,n-32,z),(e+23,n+32,z+14),'steel')
    # Hero pump tower: curved segmented wall, bands, panel ribs and service crown.
    c=np.array((180,510));r=242
    tower.cylinder(c,r,-150,792,'concrete',sides=64,surface='default')
    for z in [-110,160,400,680,787]:
        torus(tower,(*c,z),(0,0,1),r+1,5,'steel',64)
    for th in np.linspace(0,2*math.pi,16,endpoint=False):
        p=c+(r+4)*np.array([math.cos(th),math.sin(th)])
        tube(tower,(*p,-145),(*p,794),3.5,'steel',10)
        for z in [180,420,690]:tube(tower,(*p,z),(*p,z+8),6,'rust',10)
    tower.cylinder(c,293,782,792,'grate',sides=64,surface='metal')
    for i in range(64):
        a=2*math.pi*i/64;b=2*math.pi*(i+1)/64
        rail(tower,c+293*np.array([math.cos(a),math.sin(a)]),c+293*np.array([math.cos(b),math.sin(b)]),792,collide=False)
    for e,n in [(-85,500),(70,520),(210,560),(340,510)]:
        tower.cylinder((e,n),26,792,845,'steel',sides=16)
        tower.cylinder((e,n),29,842,848,'rust',sides=16)
        pipe(pipes,[(e,n,848),(e,n,882),(e,n+58,882)],10,bolts=False)
    tower_stencil(signs,'tower_sign',c,r+1.4,491,(300,432))
    # Main raised gate platform, connected to the perimeter by two bridges and stair flights.
    catwalk(walks,(-145,90),(580,268),160)
    catwalk(walks,(-720,125),(-145,255),160)
    catwalk(walks,(580,125),(850,255),160)
    for e in [-120,550]:
        walks.box((e-16,110,-150),(e+16,250,160),'steel','metal')
        walks.beam((e,114,-120),(e,248,140),(10,10),'rust')
    for a,b in [((-145,95),(580,95)),((-145,264),(0,264)),((390,264),(580,264)),((-700,125),(-145,125)),((-700,255),(-145,255)),((580,125),(840,125)),((580,255),(840,255))]:rail(walks,a,b,160)
    # Gate A headwall, open under the bridge, with an overflowing sluice.
    for e in [-90,390]:shell.box((e-24,245,-150),(e+24,305,160),'brick','default')
    shell.box((-115,245,82),(415,305,147),'concrete','default')
    signface(signs,'gate',(150,243,112),(1,0,0),(0,0,1),(380,65))
    for z in [-20,32,65]:pipes.box((-65,263,z),(365,275,z+8),'steel')
    # Ground to gate and catwalk stairs form a continuous circuit.
    stairs(walks,-925,-765,-100,300,0,160)
    catwalk(walks,(-945,300),(-690,420),160)
    catwalk(walks,(-735,125),(-620,420),160)
    stairs(walks,785,935,-430,-30,0,160)
    catwalk(walks,(765,-30),(950,330),160)
    stairs(walks,-925,-765,300,740,160,352)
    catwalk(walks,(-950,740),(950,940),352)
    # A second accessible high circuit, the reference's asymmetric stacked balconies.
    stairs(walks,-715,-565,760,285,352,544)
    catwalk(walks,(-950,115),(-560,285),544)
    catwalk(walks,(-950,-570),(-770,115),544)
    stairs(walks,785,935,310,750,160,352)
    stairs(walks,565,715,760,300,352,544)
    catwalk(walks,(565,110),(950,300),544)
    catwalk(walks,(770,-550),(950,110),544)
    catwalk(walks,(-950,285),(-770,940),544)
    catwalk(walks,(770,300),(950,940),544)
    catwalk(walks,(-770,850),(770,980),544)
    # High tower access continues from the back mezzanine.
    stairs(walks,-470,-320,900,410,544,792)
    catwalk(walks,(-560,760),(-300,940),544)
    catwalk(walks,(-470,300),(20,410),792)
    for a,b,z in [((-750,-540),(-750,110),544),((750,-540),(750,110),544),((-530,760),(-300,760),544),((-770,850),(-490,850),544),((-300,850),(770,850),544),((-750,285),(-750,830),544),((750,300),(750,830),544),((-950,940),(950,940),352),((-450,305),(20,305),792)]:rail(walks,a,b,z)
    # Ground promenade rails interrupted at stairs and in/out paths.
    for a,b in [((-610,-550),(-610,-190)),((-610,290),(-610,720)),((730,-550),(730,100)),((-600,-570),(720,-570))]:rail(walks,a,b,0)
    for e in [-900,-700,800,925]:
        for n in [120,260,750]:
            tube(walks,(e,n,-150),(e,n,350),6,'rust',10)
            walks.beam((e,n,180),(e-95,n,270),(5,7),'steel')
    # Twin prominent discharge elbows on the tower shoulders.
    for e in [-48,408]:
        points=[(e,490,660),(e,320,660)]
        for t in np.linspace(0,math.pi/2,9)[1:]:points.append((e,320-52*math.sin(t),608+52*math.cos(t)))
        points.append((e,268,580))
        pipe(pipes,points,34,open_end=True)
        # Two crossing curved sheets make a voluminous falling stream.
        for rot in [0,.5*math.pi]:
            widths=np.linspace(27,39,25)
            for k in range(24):
                t0=k/24;t1=(k+1)/24
                def p(t,side):
                    x=e+side*(27+12*t)*math.cos(rot)
                    y=258-70*t+side*(27+12*t)*math.sin(rot)
                    return (x,y,580-700*t)
                falls.polygon('fall',[p(t0,-1),p(t0,1),p(t1,1),p(t1,-1)],uv=[(0,t0*6),(1,t0*6),(1,t1*6),(0,t1*6)],both_sides=True)
        for rr in [50,80,110]:
            for i in range(32):
                a=2*math.pi*i/32;b=2*math.pi*(i+1)/32
                def p(t,r):return (e+r*math.cos(t),188+r*math.sin(t),-117+RNG.uniform(0,.3))
                falls.polygon('foam',[p(a,rr-6),p(a,rr+6),p(b,rr+6),p(b,rr-6)],uv=[(0,0),(1,0),(1,1),(0,1)],both_sides=True)
        LIGHTS.append((np.array((e,120,-60)),(.14,.6,.32),410,False))
    # Lower tower U-pipes and the front-side outfall.
    for e in [-5,370]:
        pipe(pipes,[(e,262,70),(e,262,280),(e,250,315),(e+45,235,335),(e+80,220,310),(e+80,200,240)],23)
    pipe(pipes,[(860,-550,48),(620,-550,48),(535,-520,15),(535,-460,-30)],44,open_end=True)
    for k in range(16):
        t=k/16;s=(k+1)/16
        falls.polygon('fall',[(500,-455+t*75,-30-t*90),(568,-455+t*75,-30-t*90),(574,-455+s*75,-30-s*90),(494,-455+s*75,-30-s*90)],uv=[(0,t),(1,t),(1,s),(0,s)],both_sides=True)
    for e in [10,100,190,280]:
        falls.polygon('fall',[(e-35,244,34),(e+35,244,34),(e+44,174,-118),(e-44,174,-118)],uv=[(0,0),(1,0),(1,2),(0,2)],both_sides=True)
    # Heavy pipe banks, overhead runs, valves, brackets and hanging crane blocks.
    for z in [282,325,375,925,985]:
        pipe(pipes,[(-942,-960,z),(-942,980,z)],14 if z<500 else 24)
        pipe(pipes,[(940,-960,z),(940,980,z)],17 if z<500 else 27)
    for e in [-700,-630,-545,650,720]:
        pipe(pipes,[(e,-980,1015),(e,1000,1015)],22)
    for e in [-984,-958,-932]:
        pipe(pipes,[(e,-650,5),(e,-650,360),(e,-650,720),(e,-570,795),(e,940,795)],12)
    for e,n,z in [(-958,-650,195),(872,-320,80),(-940,420,220),(930,620,310)]:
        torus(pipes,(e,n,z),(0,1,0),22,2.8,'rust',24)
        for t in np.linspace(0,2*math.pi,5,endpoint=False):tube(pipes,(e,n,z),(e+20*math.cos(t),n,z+20*math.sin(t)),1.7,'steel',8)
        tube(pipes,(e,n-14,z),(e,n+14,z),4,'steel',12)
    for e,n,z in [(610,-20,740),(820,240,680)]:
        for off in [-13,13]:
            for h in np.arange(z+30,1120,13):torus(detail,(e+off,n,h),(1,0,0) if int(h/13)%2 else (0,1,0),5,1.2,'steel',12)
        detail.box((e-23,n-20,z),(e+23,n+20,z+84),'yellow')
        for h in range(0,75,22):detail.beam((e-23,n-21,z+h),(e+23,n-21,z+h+22),(9,2),'steel')
        # Curved hook.
        pts=[(e+18*math.cos(t),n,z-23+27*math.sin(t)) for t in np.linspace(-math.pi*.95,math.pi*.45,16)]
        for a,b in zip(pts,pts[1:]):tube(detail,a,b,6,'steel',12)
    # Wall stencils and utility signage mirror the reference's locations.
    for paint,c,right,size in [
        ('cleaner',(-973,-140,400),(0,1,0),(245,300)),('flow',(-970,-230,235),(0,1,0),(260,90)),
        ('still',(-970,-52,120),(0,1,0),(120,130)),('sector',(-972,275,270),(0,1,0),(170,170)),
        ('progress',(-450,1017,605),(1,0,0),(240,330)),('purify',(973,200,410),(0,-1,0),(200,260)),
        ('buried',(971,-100,180),(0,-1,0),(150,215)),('number',(762,106,644),(1,0,0),(110,115)),
        ('warning',(-615,-400,35),(0,-1,0),(110,65)),('direction',(-570,-50,700),(1,0,0),(250,145))]:
        signface(signs,paint,c,right,(0,0,1),size)
    # Work lamps are placed as visible fixtures, not unexplained point lights.
    for p in [(-960,-560,310),(-720,-600,52),(-680,-110,205),(-850,260,226),(-900,670,414),(-380,920,424),(460,920,424),(900,620,414),(880,-300,220),(-850,-380,610),(850,-350,610),(-360,180,610),(470,180,610)]:lamp(detail,p,'amber',360,1.6)
    for p in [(-100,240,815),(410,320,815),(250,780,815)]:lamp(detail,p,'amber',330,1.2)
    lamp(detail,(-940,-230,220),'green',205,1.7)
    for p in [(935,80,228),(-900,270,175),(835,280,175)]:lamp(detail,p,'red',205,1.7)
    for p in [(-820,510,120),(820,520,130),(145,215,55),(-200,-800,240)]:lamp(detail,p,'white',390,1.4)
    # Broad light reflected off wet concrete, kept dim so work lamps remain focal.
    for p in [(-500,0,410),(500,320,410),(-180,-620,340)]:LIGHTS.append((np.array(p),(.065,.13,.11),1100,False))
    # Barrels, ruptured drums, power cabinets, cable trays and piled rubble.
    for e,n,z in [(-670,-680,0),(-956,-430,0),(-710,640,0),(820,-650,0),(850,500,0),(-580,830,352)]:
        detail.cylinder((e,n),20,z,z+54,'rust',sides=24,surface='metal')
        for h in [3,17,40,51]:torus(detail,(e,n,z+h),(0,0,1),20,1.3,'steel',24)
        detail.cylinder((e+8,n-5),3,z+54,z+56,'steel',sides=10)
    for e,n,z in [(-958,470,0),(946,600,0),(-870,830,352)]:
        detail.box((e-18,n-38,z),(e+18,n+38,z+115),'steel','metal')
        for h in range(30,90,8):detail.box((e-19,n-25,z+h),(e+19,n+25,z+h+2),'rust')
        lamp(detail,(e,n-40,z+104),'green',100,.5)
    for _ in range(180):
        side=RNG.choice([-1,1]); e=side*RNG.uniform(900,960); n=RNG.uniform(-900,970)
        sx,sy,sz=RNG.uniform(3,15,3)
        detail.box((e-sx,n-sy,0),(e+sx,n+sy,sz),'brick' if RNG.random()<.65 else 'rust')
    # Small grime chips and stagnant froth at the basin edges.
    for _ in range(65):
        e=RNG.uniform(-550,690); n=RNG.choice([-530,735])+RNG.uniform(-20,20)
        rr=RNG.uniform(3,12)
        detail.cylinder((e,n),rr,-118.8,-118.2,'rust',sides=6)
    water.polygon('water',[(-620,-580,-120),(740,-580,-120),(740,780,-120),(-620,780,-120)])
    return {'shell':shell,'tower':tower,'catwalks':walks,'pipework':pipes,'details':detail,'signage':signs,'water':water,'cascades':falls}

def scene(models):
    objects=[]
    go=lambda name,key,**kw:K.game_object(IDS,name,key,**kw)
    comp=lambda ty,key,**kw:K.component(IDS,ty,key,**kw)
    objects.append(go('Sewage map information','info',components=[
        comp('Sandbox.SceneInformation','info/scene',Title='Sewage',Description='Ravenholm Waterworks. A flooded industrial pump chamber, stacked catwalks and infected service tunnels.',SceneTags='zombies,sewage,industrial'),
        comp('Facepunch.MapInformation','info/map',Image='ui/maps/sewage.png',IsVisibleInMenu=True,ZombiesOnly=True),
        comp('Facepunch.MapSpawnSettings','info/spawns',UseMapSpawnPoints=False,AllowNavMeshSpawns=False)]))
    for name in models:
        path=f'models/maps/sewage/sewage_{name}.vmdl'
        c=[comp('Sandbox.ModelRenderer',name+'/render',Model=path)]
        if name not in ('water','cascades','signage'):c.append(comp('Sandbox.ModelCollider',name+'/collision',Model=path,Static=True))
        objects.append(go('Waterworks '+name,name,components=c,tags='sewage'+(',water' if name=='water' else '')))
    lights=[]
    for i,(p,color,radius,shadows) in enumerate(LIGHTS):
        lights.append(go(f'Work light {i+1}',f'light/{i}',position=K.to_world(p),components=[comp('Sandbox.PointLight',f'light/{i}/component',LightColor=','.join(map(str,(*color,1))),Radius=radius,Shadows=shadows,Attenuation=1,FogMode='Enabled',FogStrength=.5)]))
    objects.append(go('Practical work lights','lights',children=lights))
    objects.append(go('Ambient reflected green','ambient',components=[comp('Sandbox.AmbientLight','ambient/light',Color='0.055,0.082,0.065,1')]))
    objects.append(go('Chamber atmosphere','fog',components=[
        comp('Sandbox.GradientFog','fog/gradient',Color='0.055,0.10,0.078,0.7',StartDistance=350,EndDistance=3400,FalloffExponent=1.8,Height=900,VerticalFalloffExponent=1),
        comp('Sandbox.VolumetricFogController','fog/controller')]))
    objects.append(go('Basin mist','mist',position=K.to_world((100,100,-80)),components=[comp('Sandbox.VolumetricFogVolume','mist/volume',Bounds={'Mins':'-650,-640,-80','Maxs':'650,640,80'},Color='0.20,0.35,0.24,1',Strength=.065,FalloffExponent=2)]))
    for i,p in enumerate([(-540,-470,180),(400,380,220),(-20,450,670)]):
        objects.append(go(f'Chamber reflection {i}',f'probe/{i}',position=K.to_world(p),components=[comp('Sandbox.EnvmapProbe',f'probe/{i}/c',Mode='Baked',Bounds={'Mins':'-1300,-1300,-700','Maxs':'1300,1300,700'},Feathering=200,ZFar=3000)]))
    spawns=[(-805,-800,4),(-725,-800,4),(-805,-710,4),(-725,-710,4)]
    # Co-op starts together; the Zombie round system samples reachable navmesh elsewhere.
    objects.append(go('Co-op spawn landing','spawns',children=[go(f'Survivor {i+1}',f'spawn/{i}',position=K.to_world(p),rotation=K.yaw_rotation(-20),components=[comp('TeamSpawnPoint',f'spawn/{i}/c',Team='CounterTerrorist')]) for i,p in enumerate(spawns)]))
    objects.append(K.prefab_instance(IDS,'prefabs/game_modes/zombies.prefab'))
    objects.append(K.prefab_instance(IDS,'scenes/maps/defusemap_01/game_setup.prefab'))
    # Keep the reference camera out of runtime so it cannot override the survivor.
    preview=go('Reference composition camera','camera',position=K.to_world((-870,-650,90)),rotation=K.angles_rotation(-9,-25),components=[comp('Sandbox.CameraComponent','camera/c',FieldOfView=100,BackgroundColor='0.012,0.021,0.017,1',IsMainCamera=False)])
    preview['Flags']=2048  # GameObjectFlags.EditorOnly in engine 26.10.13.
    objects.append(preview)
    data={'__guid':IDS('scene'),'GameObjects':objects,'SceneProperties':{'NetworkInterpolation':True,'PhysicsMode':'Physics3D','TimeScale':1,'WantsSystemScene':True,
          'Metadata':{'Title':'Sewage','Image':'ui/maps/sewage.png','IsVisibleInMenu':'True','ZombiesOnly':'True','GameModes':'prefabs/game_modes/zombies.prefab'},
          'NavMesh':{'Enabled':True,'IncludeStaticBodies':True,'IncludeKeyframedBodies':True,'EditorAutoUpdate':True,'AgentHeight':72,'AgentRadius':16,'AgentStepSize':18,'AgentMaxSlope':40,'ExcludedBodies':'zone','IncludedBodies':'','DeferGeneration':False,'CustomBounds':True,'Bounds':{'Mins':'-1000,-1540,-180','Maxs':'1040,1540,900'}}},
          'ResourceVersion':3,'Title':'Sewage','Description':'Ravenholm Waterworks','__references':[],'__version':3}
    K.write_text(ROOT/'output/sewage/scene-import.json',json.dumps(data,indent=2))
    K.write_text(ROOT/'output/sewage/route-checks.json',json.dumps({'spawn':list(K.to_world(spawns[0])), 'destinations':[list(K.to_world(p)) for p in [(-820,-220,5),(860,100,5),(-680,230,164),(830,230,164),(-820,840,356),(820,840,356),(-820,-350,548),(820,-350,548),(0,900,548),(0,350,796),(0,-100,-145)]]},indent=2))

def main():
    materials(); models=build(); stats={}
    for name,m in models.items():
        stats[name]={'triangles':K.write_model(MOD,'models/maps/sewage','sewage_'+name,m),'boxes':len(m.boxes),'hulls':len(m.hulls)}
    scene(models)
    K.write_text(ROOT/'output/sewage/build-report.json',json.dumps(stats,indent=2))
    print(json.dumps({'models':stats,'lights':len(LIGHTS),'stage':str(STAGE)},indent=2))

if __name__=='__main__':main()
