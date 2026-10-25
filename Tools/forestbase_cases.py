"""Military hard cases matching the user's 5x4 reference. Shared PBR atlases;
actual lid joints, catches, corner caps and recessed handles; original physics.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import map_kit as K

COLORS=[(67,76,50),(160,135,91),(44,46,44),(139,143,139),(81,87,55),
 (162,134,88),(76,83,54),(155,155,145),(70,79,47),(43,44,41),
 (101,129,139),(64,79,57),(165,136,89),(62,78,57),(193,152,23),
 (40,44,43),(76,83,54),(46,78,103),(149,153,151),(62,77,54)]
IDS=['A-17','B-03','C-21','D-04','','E-16','','F-09','G-12','H-08',
 'I-25','J-14','K-07','L-11','M-19','N-02','O-18','P-21','Q-23','R-10']
RESOURCE='materials/forestbase/transit'

def uv(i,u,v,cols=5,rows=4):
    pad=.016
    return ((i%cols+pad+u*(1-2*pad))/cols,1-(i//cols+1-pad-v*(1-2*pad))/rows)

def case(m,e,n,z,w,h,paint,api,variant=None,solid=True):
    if solid:m.collision_box((e-w/2,n-w*.38,z),(e+w/2,n+w*.38,z+h),'wood')
    if isinstance(m,api['CollisionOnlyModel']):return
    for p in ('front','shell','hardware'):
        m.material_overrides['transit_'+p]=f'{RESOURCE}/{p}.vmat'
        m.tile_overrides['transit_'+p]=66
    i=int(abs(e*11.7+n*7.9+z*3.3+w*1.13))%20 if variant is None else variant
    s=w/66;front=n-w*.38;back=n+w*.38;seam=z+h*.82
    def part(a,b,slot=0,r=0):
        p=K.Model()
        if r:api['bevel_box'](p,a,b,'part',r)
        else:api['box'](p,a,b,'part')
        for pts,norm in p.polygons['part']:
            axis=int(np.argmax(np.abs(norm)));axes=(0,2) if axis==1 else (1,2) if axis==0 else (0,1)
            coords=[uv(slot,(q[axes[0]]-a[axes[0]])/(b[axes[0]]-a[axes[0]]),
                        (q[axes[1]]-a[axes[1]])/(b[axes[1]]-a[axes[1]]),4,2) for q in pts]
            m.polygon('transit_hardware',pts,normal=norm,uv=coords)
    hx0=e-w*.155;hx1=e+w*.155;hz0=z+h*.39;hz1=z+h*.65
    def shell(a,b):
        p=K.Model();api['bevel_box'](p,a,b,'part',min(w*.035,2.1))
        for pts,norm in p.polygons['part']:
            # Keep the outer corners round but flatten the meeting bevels of
            # lid and body, leaving a narrow gasket instead of an open groove.
            radius=min(w*.035,2.1,float(min(np.array(b)-a))*.24)
            pts=[q.copy() for q in pts]
            for q in pts:
                if a[2]==z and q[2]>=b[2]-radius-.0001:
                    q[2]=b[2]-(b[2]-q[2])*.18/radius
                elif a[2]!=z and q[2]<=a[2]+radius+.0001:
                    q[2]=a[2]+(q[2]-a[2])*.18/radius
            axis=int(np.argmax(np.abs(norm)));surfaces=[pts]
            if abs(norm[1])>.999 and a[2]==z:
                # Cut out the handle well on the two broad faces.
                x0=min(q[0] for q in pts);x1=max(q[0] for q in pts)
                z0=min(q[2] for q in pts);z1=max(q[2] for q in pts);yy=pts[0][1]
                surfaces=[]
                for xa,za,xb,zb in [(x0,z0,x1,hz0),(x0,hz1,x1,z1),(x0,hz0,hx0,hz1),(hx1,hz0,x1,hz1)]:
                    q=[(xa,yy,za),(xb,yy,za),(xb,yy,zb),(xa,yy,zb)]
                    if norm[1]>0:q.reverse()
                    surfaces.append(q)
            for q in surfaces:
                if axis==1:coords=[uv(i,(v[0]-e+w/2)/w,(v[2]-z)/h) for v in q]
                elif axis==0:coords=[uv(i,(v[1]-front)/(w*.76),(v[2]-z)/h) for v in q]
                else:coords=[uv(i,(v[0]-e+w/2)/w,(v[1]-front)/(w*.76)) for v in q]
                m.polygon('transit_front' if norm[1]<-.999 else 'transit_shell',q,uv=coords)
    shell((e-w/2,front,z),(e+w/2,back,seam-.15*s))
    shell((e-w/2,front,seam+.15*s),(e+w/2,back,z+h))
    part((e-w/2+s,front+s,seam-.18*s),(e+w/2-s,back-s,seam+.18*s),2)
    # Compact corner guards replace the old full-height cage rails.
    for xx in (-1,1):
        for yy in (-1,1):
            for zz in (0,1):
                x=e+xx*(w/2-1.7*s);y=n+yy*(w*.38-1.7*s);base=z+(h-4.8*s if zz else 0)
                part((x-2.1*s,y-2.1*s,base),(x+2.1*s,y+2.1*s,base+4.8*s),0,.65*s)
    catch={8:3,15:4,18:5}.get(i,0)
    for sign,edge in ((-1,front),(1,back)):
        for x in (e-w*.29,e+w*.29):
            ya,yb=sorted((edge+sign*.16*s,edge+sign*s))
            part((x-2.4*s,ya,seam-8.5*s),(x+2.4*s,yb,seam+4*s),0,.45*s)
            ya,yb=sorted((edge+sign*1.05*s,edge+sign*1.7*s))
            part((x-1.5*s,ya,seam-7*s),(x+1.5*s,yb,seam+1.8*s),catch,.38*s)
            part((x-2.7*s,ya,seam+.6*s),(x+2.7*s,yb,seam+2.5*s),1)
            part((x-.8*s,ya-.05*s,seam-4.8*s),(x+.8*s,yb+.05*s,seam-3.3*s),2)
        ya,yb=sorted((edge-sign*1.4*s,edge-sign*.6*s))
        part((hx0,ya,hz0),(hx1,yb,hz1),2)
        outer=[(hx0,edge,hz0),(hx1,edge,hz0),(hx1,edge,hz1),(hx0,edge,hz1)]
        inner=[(x,edge-sign*.65*s,zz) for x,_,zz in outer]
        for k in range(4):
            q=[outer[k],outer[(k+1)%4],inner[(k+1)%4],inner[k]]
            if sign>0:q.reverse()
            m.polygon('transit_hardware',q,uv=[uv(0,u,v,4,2) for u,v in ((0,0),(1,0),(1,1),(0,1))])
        ya,yb=sorted((edge-sign*.7*s,edge+sign*.2*s))
        for x in (hx0+1.6*s,hx1-1.6*s):
            part((x-.8*s,ya,hz0+1.5*s),(x+.8*s,yb,hz1-1.2*s),0)
            part((x-1.3*s,ya-.15*s,hz1-2.5*s),(x+1.3*s,yb+.15*s,hz1-1.2*s),1)
        part((hx0+1.5*s,ya,hz0+1.5*s),(hx1-1.5*s,yb,hz0+3*s),0)
    for y in (n-w*.20,n+w*.20):part((e-w*.32,y-.65*s,z+h-.2*s),(e+w*.32,y+.65*s,z+h+.45*s),0)

def generate_materials(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);size=512
    font=lambda px:ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',px)
    def base(i,color,hardware=False):
        rng=np.random.default_rng(6013+i)
        fine=rng.normal(0,1.45,(size,size))
        cloud=np.asarray(Image.fromarray(rng.integers(70,185,(32,32),dtype=np.uint8)).resize((size,size),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(4)),float)-127
        a=np.clip(np.array(color)[None,None,:]+fine[:,:,None]+cloud[:,:,None]*.09,0,255).astype('uint8')
        im=Image.fromarray(a);d=ImageDraw.Draw(im)
        if i in (4,5) and not hardware:
            camo=[(39,44,32),(114,109,75),(76,75,52)] if i==4 else [(83,75,54),(123,105,72),(180,151,99)]
            for k in range(58):
                x,y=rng.integers(-60,520,2);rx,ry=rng.integers(14,65,2)
                d.polygon([(x+math.cos(t)*rx*rng.uniform(.7,1.3),y+math.sin(t)*ry*rng.uniform(.7,1.3)) for t in np.linspace(0,math.tau,13,endpoint=False)],fill=camo[k%3])
        return im,rng
    def marks(im,i,rng):
        d=ImageDraw.Draw(im);ivory=(194,191,164);ink=(40,43,36)
        contrast=ink if i in (1,3,5,7,10,12,14,18) else ivory
        if i in (7,11,19):d.polygon([(230,495),(302,495),(490,163),(490,61)],fill=(160,44,30) if i==7 else (185,186,157))
        if i in (2,14):
            for y in range(-200,700,112):d.polygon([(433,y),(494,y-71),(494,y-16),(433,y+55)],fill=(181,148,30) if i==2 else (43,48,39))
        if i==17:d.polygon([(295,305),(352,305),(436,388),(352,470),(295,470),(380,388)],fill=ivory)
        if i==6:
            d.ellipse((49,331,165,447),outline=ivory,width=7)
            d.polygon([(107+math.cos(-math.pi/2+k*math.pi/5)*(58 if k%2==0 else 23),389+math.sin(-math.pi/2+k*math.pi/5)*(58 if k%2==0 else 23)) for k in range(10)],fill=ivory)
        if i in (13,18):
            for y in range(315,430,13):
                for x in list(range(43,164,13))+list(range(345,461,13)):d.ellipse((x,y,x+4,y+5),fill=(28,32,29))
        if IDS[i]:
            mask=Image.new('L',(220,72));md=ImageDraw.Draw(mask);md.text((0,-3),IDS[i],font=font(51),fill=235);cursor=0
            for c in IDS[i]:
                width=font(51).getlength(c);md.rectangle((cursor+width*.48,0,cursor+width*.48+2,71),fill=0);cursor+=width
            im.paste(contrast,(52,366),mask)
        d=ImageDraw.Draw(im)
        if i not in (13,18):
            d.rectangle((319,406,455,464),fill=(187,181,153),outline=(77,77,61),width=2)
            d.text((325,410),'FIELD / TRANSIT',font=font(10),fill=ink);d.text((325,421),'HC1 MATERIAL CONTROL',font=font(8),fill=ink)
            for x in range(325,449,3):d.rectangle((x,435,x+int(rng.integers(1,3)),451-int(rng.integers(0,5))),fill=ink)
            d.text((325,453),f'0418 {i:02d} 881016',font=font(8),fill=ink)
        if i in (1,8):
            c=(192,155,30) if i==8 else ink;d.polygon([(402,318),(424,355),(380,355)],outline=c,width=4);d.text((397,325),'!',font=font(22),fill=c)
        if i==15:
            d.rectangle((382,353,447,421),outline=ivory,width=3);d.rectangle((405,363,424,410),fill=ivory);d.rectangle((391,378,439,395),fill=ivory)
        if i==12:
            for y in (365,383):d.line([(393,y+12),(415,y),(437,y+12)],fill=ink,width=6)
    def wear(im,rng,metal=False):
        d=ImageDraw.Draw(im)
        for k in range(1900):
            edge=int(rng.integers(4));p=float(rng.uniform(9,503));depth=float(rng.exponential(5)+10)
            x,y=(p,depth) if edge==0 else (p,512-depth) if edge==1 else (depth,p) if edge==2 else (512-depth,p)
            length=float(rng.uniform(1,11));c=((127,132,129) if metal else (128,123,103)) if k%3 else (39,42,36)
            d.line((x,y,x+length if edge<2 else x+1,y+1 if edge<2 else y+length),fill=c,width=int(rng.integers(1,3)))
        for k in range(150):
            x,y=rng.uniform(25,487,2);d.line((x,y,x+float(rng.uniform(1,15)),y+float(rng.uniform(-1.2,1.2))),fill=((92,96,93) if metal else (92,92,75)) if k%4 else ((144,148,145) if metal else (144,139,117)),width=1)
        arr=np.asarray(im).astype(float);dust=np.clip((np.arange(512)[:,None]-400)/112,0,1)*(.03 if metal else .1)
        return Image.fromarray(np.clip(arr*(1-dust[:,:,None])+np.array((102,92,65))*dust[:,:,None],0,255).astype('uint8'))
    front=Image.new('RGB',(size*5,size*4));shell=front.copy();hardware=Image.new('RGB',(size*4,size*2))
    for i,c in enumerate(COLORS):
        im,rng=base(i,c);plain=im.copy();marks(im,i,rng)
        front.paste(wear(im,rng),(i%5*size,i//5*size));shell.paste(wear(plain,rng),(i%5*size,i//5*size))
    for i,c in enumerate([(42,45,42),(111,112,99),(18,21,19),(178,142,18),(130,38,28),(180,80,13),(185,185,158),(82,85,79)]):
        im,rng=base(i,c,True);hardware.paste(wear(im,rng,True),(i%4*size,i//4*size))
    for name,im in [('front',front),('shell',shell),('hardware',hardware)]:
        # Source 2's mip generator requires power-of-two texture dimensions.
        if name!='hardware':im=im.resize((2048,2048),Image.Resampling.LANCZOS)
        im.save(out/(name+'_color.png'),optimize=True);rng=np.random.default_rng(700+len(name));hh,ww=im.height,im.width
        normal=np.empty((hh,ww,3),dtype='uint8');normal[:]=[128,128,255];normal[:,:,:2]=np.clip(rng.normal(128,.7,(hh,ww,2)),0,255).astype('uint8')
        Image.fromarray(normal).save(out/(name+'_normal.png'),optimize=True)
        rough=np.clip(rng.normal(161 if name=='hardware' else 191,2,(hh,ww)),0,255).astype('uint8');Image.fromarray(rough).convert('RGB').save(out/(name+'_rough.png'),optimize=True)
        metal=.65 if name=='hardware' else .08
        tint='0.72 0.72 0.72' if name!='hardware' else '1 1 1'
        (out/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/forestbase_coating.shader"\n F_SPECULAR "1"\n'+f' CoatingTint "[{tint}]"\n g_flMetalness "{metal}"\n TextureMetalness "[{metal} {metal} {metal} 0]"\n g_flCoatingMetalness "{metal}"\n'+''.join(f' Texture{k} "{RESOURCE}/{name}_{v}.png"\n' for k,v in [('Color','color'),('Normal','normal'),('Roughness','rough')])+' TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_flModelTintAmount "1"\n}\n')
    return front
