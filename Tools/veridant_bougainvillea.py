"""A branching pergola vine with folded leaves and small papery flower bracts."""
import math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import riverdale_parts as P

UP=np.array((0.,0.,1.))
RESOURCE='materials/veridant/pergola-flowers-v2'
MATERIALS={f'vr_bv_{name}':f'{RESOURCE}/{name}.vmat'
           for name in ('leaf_dark','leaf_light','rose','wine','pale','centre')}


def blade(model,base,direction,normal,length,width,paint,phase=0.,paper=False):
    """Closed shading on both sides of an ovate blade, with a raised midrib."""
    u=P.unit(direction);v=P.unit(np.cross(normal,u));n=np.cross(u,v)
    points=[np.array(base)];coords=[(.5,0.)]
    rows=(.24,.67) if paper else (.18,.48,.76)
    for t in rows:
        half=width*.5*math.sin(math.pi*t)**.78
        for side in (-1,0,1):
            lateral=side*half*(1+.045*math.sin(phase+t*7+side))
            ridge=(.075 if paper else .045)*length*math.sin(math.pi*t)*(1-abs(side))
            curl=.07*length*t*t-.028*length*abs(side)*math.sin(math.pi*t)
            points.append(np.array(base)+u*(length*t)+v*lateral+n*(ridge+curl))
            coords.append(((side+1)/2,t))
    tip=len(points);points.append(np.array(base)+u*length+n*length*.08);coords.append((.5,1.))
    faces=[(0,1,2),(0,2,3)]
    for start in range(1,1+3*(len(rows)-1),3):
        faces.extend(((start,start+3,start+4,start+1),(start+1,start+4,start+5,start+2)))
    last=1+3*(len(rows)-1)
    faces.extend(((last,tip,last+1),(last+1,tip,last+2)))
    normals=np.zeros((len(points),3))
    for face in faces:
        for j in range(1,len(face)-1):
            ids=[face[0],face[j],face[j+1]];a,b,c=(points[i] for i in ids)
            normal=np.cross(b-a,c-a)
            assert np.linalg.norm(normal)>1e-8
            normals[ids]+=normal
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    assert np.isfinite(normals).all()
    for face in faces:
        model.polygon(paint,[points[i] for i in face],normals=[normals[i] for i in face],uv=[coords[i] for i in face])
        reverse=face[::-1]
        model.polygon(paint,[points[i] for i in reverse],normals=[-normals[i] for i in reverse],uv=[coords[i] for i in reverse])


def build_into(model,at,right,w,h,seed=0,off=2.):
    rng=np.random.default_rng(abs(int(seed)));at=np.array(at,float);right=P.unit(right)
    out=P.unit(np.cross(right,UP));model.material_overrides.update(MATERIALS)
    model.material_overrides['vr_bark']='materials/veridant/vr_bark.vmat'
    model.tile_overrides.update({paint:12. for paint in MATERIALS})
    model.tile_overrides['vr_bark']=64.
    stats={'leaves':0,'flower_clusters':0,'bracts':0,'woody_branches':0}

    def stem(path,r=.12):
        P.tube(model,path,r,'vr_bark',sides=6,bend_radius=r*1.5)
        stats['woody_branches']+=1

    def leaf(point,axis,phase):
        direction=P.unit(axis*.28+right*rng.uniform(-.9,.9)+out*rng.uniform(-.45,.65)+UP*rng.uniform(.1,.8))
        normal=P.unit(out*rng.uniform(.4,1.)+UP*rng.uniform(.15,.85)+right*rng.uniform(-.3,.3))
        length=rng.uniform(3.0,4.5)
        blade(model,point,direction,normal,length,length*rng.uniform(.46,.64),
              'vr_bv_leaf_dark' if rng.random()<.64 else 'vr_bv_leaf_light',phase)
        stats['leaves']+=1

    def flower(point,phase):
        normal=P.unit(out*rng.uniform(.45,1.)+UP*rng.uniform(.25,.8)+right*rng.uniform(-.6,.6))
        a=P.unit(np.cross(normal,UP));b=np.cross(normal,a)
        for floret in range(int(rng.integers(2,4))):
            origin=point+a*rng.uniform(-.65,.65)+b*rng.uniform(-.65,.65)+normal*rng.uniform(-.2,.4)
            tone=rng.choice(('vr_bv_rose','vr_bv_wine','vr_bv_pale'),p=(.50,.30,.20))
            for j in range(3):
                angle=phase+j*math.tau/3+rng.uniform(-.25,.25)+floret*.7
                direction=P.unit(a*math.cos(angle)+b*math.sin(angle)+normal*.42)
                length=rng.uniform(1.2,2.0)
                blade(model,origin,direction,normal,length,length*.86,tone,phase+j,paper=True)
                stats['bracts']+=1
            P.tube(model,[origin,origin+normal*.30],.075,'vr_bv_centre',sides=5)
        stats['flower_clusters']+=1

    def twig(anchor,direction,length,phase,flower_chance=.68):
        direction=P.unit(direction)
        tip=anchor+direction*length-UP*length*.16
        stem([anchor,anchor+direction*length*.48+out*.35,tip],.065)
        for j,t in enumerate(np.linspace(.10,.94,10)):
            p=anchor+direction*(length*t)-UP*length*.16*t*t
            leaf(p,direction,phase+j*.7)
        if rng.random()<flower_chance:flower(tip,phase)
        if flower_chance>.5 and rng.random()<.40:
            flower(anchor+direction*length*.60-UP*length*.16*.60**2,phase+1.9)

    # Grounded old canes climb the two existing rear posts and cross the beam.
    for sign in (-1,1):
        centre=at+right*(sign*w*.5)+out*4
        path=[]
        for t in np.linspace(0,1,18):
            angle=t*math.pi*2.2+sign*.6
            p=centre+right*(6.6*math.sin(angle))+out*(6.6*math.cos(angle))
            p[2]=max(.2,at[2]*t)+1.5*t
            path.append(p)
        stem(path,.49)
    for k in range(2):
        stem([at+right*((t-.5)*w)+out*(-4+4*math.sin(t*8+k))
              +UP*(2.1+1.4*math.sin(t*7+k)) for t in np.linspace(0,1,22)],.22 if k else .32)

    # Unequal hanging sprays leave useful negative space below the canopy.
    for index,(fraction,depth) in enumerate(((-.46,.62),(-.30,.37),(-.13,.80),(.09,.46),(.29,.67),(.46,.32))):
        phase=rng.uniform(0,math.tau);drop=h*depth

        def point(t):
            return (at+right*(fraction*w+3.2*math.sin(t*3.8+phase)*t)
                    +out*(off+5+4.8*math.sin(t*2.7+phase))-UP*(drop*t-.8*math.sin(t*4)))

        stem([point(t) for t in np.linspace(0,1,9)],.15)
        for j,t in enumerate(np.linspace(.04,.96,15)):
            side=-1 if j%2 else 1
            direction=right*side*rng.uniform(.6,1.2)+out*rng.uniform(-.5,.8)-UP*rng.uniform(.05,.65)
            twig(point(t),direction,rng.uniform(8.,14.5)*(1-.25*t),phase+j*.63)
    for j,x in enumerate(np.linspace(-w*.47,w*.47,26)):
        anchor=at+right*x+out*rng.uniform(-10,8)+UP*rng.uniform(-6,2)
        twig(anchor,right*rng.uniform(-.7,.7)+out*rng.uniform(-.8,.8)-UP*rng.uniform(.25,.9),
             rng.uniform(5,9),j*.87,flower_chance=.85)
    model.bougainvillea_stats=stats
    return model


def write_materials(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(55019);n=512
    t,x=np.mgrid[:n,:n].astype(float);t/=n-1;x=x/(n-1)*2-1
    mid=np.exp(-(x/.016)**2);veins=np.zeros_like(t)
    for base in np.arange(.12,.9,.135):
        veins+=np.exp(-((t-base-.31*np.abs(x))/.011)**2)
    noise=gaussian_filter(rng.normal(size=(n,n)),3,mode='wrap');noise/=noise.std()
    for name,paper in (('leaf',False),('bract',True)):
        height=(.0007 if paper else .0018)*mid+(.00028 if paper else .0007)*veins
        lum=.94+.065*np.sin(t*math.pi)+.012*noise+.026*veins+.032*mid
        gray=np.clip(lum*255,0,255).astype(np.uint8)
        Image.fromarray(np.repeat(gray[...,None],3,axis=2)).save(folder/f'{name}_color.png')
        dy,dx=np.gradient(height,1/n,2/n)
        normal=np.stack((-dx,dy,np.ones_like(t)),axis=-1)
        normal/=np.linalg.norm(normal,axis=-1)[...,None]
        Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype(np.uint8)).save(folder/f'{name}_normal.png')
        rough=np.clip((.84 if paper else .74)+noise*.018,0,1)*255
        Image.fromarray(rough.astype(np.uint8)).save(folder/f'{name}_rough.png')
    colours={'leaf_dark':(49,77,43),'leaf_light':(69,94,52),'rose':(171,70,101),
             'wine':(139,52,83),'pale':(185,100,119),'centre':(214,195,139)}
    for name,rgb in colours.items():
        family='leaf' if name.startswith('leaf') else 'bract'
        tint=' '.join(f'{v/255:.6f}' for v in rgb)
        text=('// Tools/veridant_bougainvillea.py\n"Layer0"\n{\n'
              '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
              '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n'
              f'    TextureColor "{RESOURCE}/{family}_color.png"\n'
              f'    TextureNormal "{RESOURCE}/{family}_normal.png"\n'
              f'    TextureRoughness "{RESOURCE}/{family}_rough.png"\n'
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
              f'    g_vColorTint "[{tint} 1]"\n    g_flModelTintAmount "1"\n}}\n')
        (folder/f'{name}.vmat').write_text(text)
