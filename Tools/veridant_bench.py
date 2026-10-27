"""Promenade bench: eased teak, individual end grain and anchored cast supports.

Dimensions and the original 72 x 18 x 18 collision envelope are retained.
All deformation is small and deterministic, with no random vertex jitter.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import map_kit as K
import riverdale_parts as P

PREFIX='materials/veridant/bench-v2'
NAMES=('teak','teak_light','teak_dark','endgrain','concrete','steel','recess','rubber')
MATERIALS={f'vr_bench_{name}':f'{PREFIX}/{name}.vmat' for name in NAMES}
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))


def stations(half,radius,interior):
    edge=np.array((0.,.13,.50,1.))*radius
    values=[-half+x for x in edge]+[half-x for x in edge]+list(interior)
    return sorted(set(round(float(x),7) for x in values if -half<=x<=half))


def rounded_member(model,centre,size,radius,paint,phase=0.,wood=False,chips=(),wood_region=0):
    """A closed rounded box with shared surface positions and analytic normals.

    Each face samples the same rounded-box projection at its boundaries.
    Localised edge losses are a continuous surface deformation, not dark decals.
    """
    centre=np.array(centre);half=np.array(size)/2
    coordinates=[stations(half[i],radius,
                 np.linspace(-half[i]+radius,half[i]-radius,max(2,math.ceil(size[i]/(7 if wood else 3))+1)))
                 for i in range(3)]
    if wood:
        coordinates[0]=stations(half[0],radius,[-half[0]+1.2,-28.,-20.,-10.,0.,10.,20.,28.,half[0]-1.2])
    core=half-radius

    def surface(raw):
        nearest=np.clip(raw,-core,core)
        normal=P.unit(raw-nearest)
        point=nearest+normal*radius
        gradient=np.zeros(3);loss=0.
        for at,spread,depth in chips:
            delta=point-np.array(at)
            amount=depth*math.exp(-float(np.dot(delta,delta))/(spread*spread))
            loss+=amount;gradient+=amount*(-2/(spread*spread))*delta
        point-=normal*loss
        gradient-=normal*np.dot(gradient,normal)
        normal=P.unit(normal+gradient)
        if wood:
            t=(point[0]+half[0])/(half[0]*2)
            # Less than two millimetres of bow over a six-foot board.
            point[1]+=.035*math.sin(math.pi*t)*math.sin(phase)
            point[2]+=.045*math.sin(math.pi*t)*math.sin(phase+2.4*t)
            # Ends have been sanded by hand; the long arrises stay straight.
            point[0]+=.025*math.sin(point[1]*2+phase)*(abs(point[0])/half[0])**12
        return point,normal

    for axis in range(3):
        other=[i for i in range(3) if i!=axis]
        for side in (-1,1):
            points={};normals={}
            for i,a in enumerate(coordinates[other[0]]):
                for j,b in enumerate(coordinates[other[1]]):
                    raw=np.zeros(3);raw[axis]=half[axis]*side
                    raw[other[0]]=a;raw[other[1]]=b
                    points[i,j],normals[i,j]=surface(raw)
            for i in range(len(coordinates[other[0]])-1):
                for j in range(len(coordinates[other[1]])-1):
                    keys=((i,j),(i+1,j),(i+1,j+1),(i,j+1))
                    pts=[points[k] for k in keys];ns=[normals[k] for k in keys]
                    if wood and axis==0:
                        material='vr_bench_endgrain'
                        uv=[(p[1]/4+.5+.07*math.sin(phase),p[2]/4+.5) for p in pts]
                    elif wood:
                        material=paint
                        across=1 if axis==2 else 2
                        # Four distinct strips from the photographic source; no
                        # texture repeats or seams within a slat's visible face.
                        uc=.13+wood_region*.24
                        uv=[(p[across]/15+uc,p[0]/(size[0]/.91)+.5+.008*math.sin(phase)) for p in pts]
                    else:
                        material=paint
                        across=other[0] if axis!=2 else 0
                        uv=[(p[across]/20+.5+phase*.035,
                             p[1]/20+.5 if axis==2 else (p[2]+half[2])/18+.05) for p in pts]
                    P.card(model,material,[centre+p for p in pts],sum(ns),uv=uv,normals=ns)


def screw(model,x,y,z):
    """A flush countersunk stainless fastener with a six-lobed recess."""
    sides=20
    rings=((.235,z+.003),(.183,z+.010),(.142,z+.016))
    for (ra,za),(rb,zb) in zip(rings,rings[1:]):
        for i in range(sides):
            a,b=math.tau*i/sides,math.tau*(i+1)/sides
            P.card(model,'vr_bench_steel',[(x+ra*math.cos(a),y+ra*math.sin(a),za),
                (x+ra*math.cos(b),y+ra*math.sin(b),za),
                (x+rb*math.cos(b),y+rb*math.sin(b),zb),(x+rb*math.cos(a),y+rb*math.sin(a),zb)],Z)
    points=[(x+.143*math.cos(a),y+.143*math.sin(a),z+.017) for a in np.linspace(0,math.tau,20,endpoint=False)]
    P.card(model,'vr_bench_steel',points,Z)
    star=[(x+r*math.cos(a),y+r*math.sin(a),z+.019)
          for i,a in enumerate(np.linspace(0,math.tau,12,endpoint=False))
          for r in [(.067 if i%2==0 else .047)]]
    P.card(model,'vr_bench_recess',star,Z)


def build_into(model,c,along,length=72.,z0=0.,collision=True):
    d=P.unit((along[0],along[1],0.));s=np.cross(Z,d);axes=np.array((d,s,Z))
    centre=np.array((c[0],c[1],z0));local=K.Model()
    seed=int(abs(c[0]*11+c[1]*7))%15437
    rng=np.random.default_rng(seed)
    phases=rng.uniform(0,math.tau,4)
    for index,y in enumerate((-6.,-2.,2.,6.)):
        size=(length-rng.uniform(.015,.085),3.4+rng.uniform(-.035,.025),2.)
        phase=float(phases[index])
        # A few millimetres of local edge loss, with none on every board.
        chips=[]
        if index in (0,3):
            chips=[((size[0]/2-.08,(-1 if index==0 else 1)*(size[1]/2-.10),.91),.36,.055)]
        paint=('vr_bench_teak','vr_bench_teak_light','vr_bench_teak','vr_bench_teak_dark')[index]
        rounded_member(local,(0,y,17.),size,.205,paint,phase,True,chips,wood_region=index)
        for x in (-length/2+8,length/2-8):
            t=(x+size[0]/2)/size[0]
            top=18.+.045*math.sin(math.pi*t)*math.sin(phase+2.4*t)
            screw(local,x,y,top)
    for index,sign in enumerate((-1,1)):
        x=sign*(length/2-8)
        # Cast concrete, with eased arrises and sparse knocks at exposed corners.
        chips=(((4.90,-7.88,6.95),.62,.16),((-4.86,7.90,-6.65),.52,.14),
               ((-4.92,-7.85,4.85),.42,.095))
        rounded_member(local,(x,0,7.80),(10.,16.,15.60),.29,
                       'vr_bench_concrete',index*.91,chips=chips)
        P.bevel_box(local,(x,0,15.70),(X,Y,Z),(9.45,15.25,.20),'vr_bench_steel',bevel=.055)
        for y in (-6.,-2.,2.,6.):
            P.bevel_box(local,(x,y,15.92),(X,Y,Z),(2.0,2.6,.16),'vr_bench_rubber',bevel=.045)
        # Downturned anchor ears make the seat/support relationship visible.
        for side in (-1,1):
            P.bevel_box(local,(x+side*4.77,0,14.70),(X,Y,Z),(.16,7.3,1.9),'vr_bench_steel',bevel=.045)
            for y in (-2.5,2.5):
                P.rod(local,(x+side*4.82,y,14.65),(x+side*4.91,y,14.65),.26,'vr_bench_steel',6,caps=True)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({name:16. for name in MATERIALS})
    for paint,rows in local.polygons.items():
        for index,(points,normal) in enumerate(rows):
            normals=local.polygon_normals.get((paint,index))
            P.card(model,paint,[centre+p@axes for p in points],normal@axes,
                   normals=[n@axes for n in normals] if normals is not None else None,
                   uv=local.polygon_uvs.get((paint,index)))
    if collision:model.oriented_box(centre+Z*9,(d,s,Z),(length,18,18),{},P.STONE)
    return {'slats':4,'fixings':8,'supports':2,'length':length,'seat_height':18.}


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(32814);h,w=2048,1024
    yy,xx=np.mgrid[0:h,0:w];x=xx/w;y=yy/h

    def noise(shape,sigma):
        a=gaussian_filter(rng.normal(size=shape),sigma,mode='wrap')
        return a/max(a.std(),1e-8)

    # Fine pores follow long fibres; broader bands wander, rather than embossing
    # the entire surface into the coarse corrugations of the original material.
    drift=noise((h,w),(190,42))*.008
    growth=np.sin((x+drift+.008*np.sin(y*math.tau*1.3))*math.tau*23)
    figure=noise((h,w),(94,8));fibres=noise((h,w),(35,1.0))
    pores=np.maximum(noise((h,w),(7,.52))-1.15,0)
    cloud=noise((h,w),(170,76))
    tone=.036*growth+.042*figure+.018*fibres+.026*cloud-.015*pores
    colour=np.array((139.,116.,86.))[None,None,:]*(1+tone[...,None])
    # Sparse darker vessel lines are low contrast and submillimetre in relief.
    colour-=pores[...,None]*np.array((1.9,1.7,1.4))
    Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(out/'teak_color.png')
    rough=np.clip(.61+.025*figure+.021*fibres+.025*pores,.49,.76)
    Image.fromarray((rough*255).astype('uint8')).save(out/'teak_rough.png')
    relief=.00065*fibres-.00085*pores+.00040*growth
    dx=(np.roll(relief,-1,1)-np.roll(relief,1,1))/(12/w)
    dy=(np.roll(relief,-1,0)-np.roll(relief,1,0))/(192/h)
    normals=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1)[...,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(out/'teak_normal.png')
    n=1024;ey,ex=np.mgrid[0:n,0:n]/n
    radial=np.sqrt(((ex-.32)*1.3)**2+((ey-.20)*.9)**2)
    ring=np.sin(radial*math.tau*44+.7*np.sin(ex*12))
    endnoise=noise((n,n),(.8,.8))
    colour=np.array((133.,112.,85.))*(1+.055*ring[...,None]+.019*endnoise[...,None])
    Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(out/'endgrain_color.png')
    base=noise((n,n),(34,34));fine=noise((n,n),(.7,.7));pores=np.maximum(noise((n,n),(1.1,1.1))-1.8,0)
    damp=np.exp(-((1-ey)/.13)**2)*(.10+.025*base)
    concrete=np.array((175.,172.,162.))*(1+.025*base[...,None]+.014*fine[...,None]-.027*pores[...,None]-damp[...,None])
    Image.fromarray(np.clip(concrete,0,255).astype('uint8')).save(out/'concrete_color.png')
    height=.0016*fine-.0045*pores
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(32/n)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(32/n)
    normals=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normals/=np.linalg.norm(normals,axis=-1)[...,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(out/'concrete_normal.png')
    Image.fromarray(np.clip((.77+.025*base+.035*pores)*255,0,255).astype('uint8')).save(out/'concrete_rough.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    metalnoise=noise((512,512),(.7,3.))
    Image.fromarray(np.clip((.35+.035*metalnoise)*255,0,255).astype('uint8')).save(out/'steel_rough.png')
    # Keep original generated PNGs in Sources. Texture mip filtering requires
    # power-of-two inputs; normalise the working copies before deriving maps.
    # Broad albedo variation does not become swollen geometry.
    source=Path(__file__).resolve().parents[1]/'Sources/Veridant/bench-v2'
    for name,filename,physical,amplitude,base_rough in (
        ('teak','teak-albedo-generated-v1.png',(15.,79.1),.0032,.64),
        ('concrete','concrete-albedo-generated-v1.png',(20.,18.),.0045,.79)):
        selected=source/filename
        assert selected.exists(),selected
        size=(1024,2048) if name=='teak' else (1024,1024)
        albedo=Image.open(selected).convert('RGB').resize(size,Image.Resampling.LANCZOS)
        albedo.save(out/f'{name}_color.png')
        pixels=np.asarray(albedo,dtype=float)/255
        gray=np.mean(pixels,axis=-1)
        detail=gray-gaussian_filter(gray,4.)
        detail=np.clip(detail/max(detail.std(),1e-6),-3,3)
        relief=detail*amplitude
        hh,ww=gray.shape
        dx=np.gradient(relief,axis=1)/(physical[0]/ww)
        dy=np.gradient(relief,axis=0)/(physical[1]/hh)
        ns=np.stack((-dx,dy,np.ones_like(gray)),axis=-1)
        ns/=np.linalg.norm(ns,axis=-1)[...,None]
        Image.fromarray(np.clip((ns*.5+.5)*255,0,255).astype('uint8')).save(out/f'{name}_normal.png')
        rough=np.clip(base_rough-detail*.025,.48,.90)
        Image.fromarray((rough*255).astype('uint8')).save(out/f'{name}_rough.png')
    for name in NAMES:
        wood=name.startswith('teak')
        colour=f'{PREFIX}/teak_color.png' if wood else f'{PREFIX}/endgrain_color.png' if name=='endgrain' else f'{PREFIX}/concrete_color.png' if name=='concrete' else 'materials/default/default_color.tga'
        normal=f'{PREFIX}/teak_normal.png' if wood else f'{PREFIX}/concrete_normal.png' if name=='concrete' else f'{PREFIX}/flat_normal.png'
        rough=f'{PREFIX}/teak_rough.png' if wood else f'{PREFIX}/concrete_rough.png' if name=='concrete' else f'{PREFIX}/steel_rough.png' if name=='steel' else '[0.68 0.68 0.68 0]'
        tint={'teak':(.84,.84,.84),'teak_light':(.90,.885,.865),'teak_dark':(.77,.79,.80),
              'concrete':(.89,.90,.91),
              'steel':(.22,.24,.235),'recess':(.027,.030,.028),'rubber':(.047,.048,.044)}.get(name,(1,1,1))
        metal=.94 if name=='steel' else 0
        text=('// Tools/veridant_bench.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
              f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
              f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
              f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1.0"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
