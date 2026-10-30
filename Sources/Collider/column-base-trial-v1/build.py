"""Review one actual Collider column base; preserve the map and all accepted props."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import psutil
proc=psutil.Process();proc.nice(psutil.IDLE_PRIORITY_CLASS);proc.cpu_affinity(proc.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import argparse,hashlib,importlib.util,json,math,re,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import scipy.ndimage as ndi
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_operators as O
import boxyard_map as B
from belltower_furniture import face
OUT=ROOT/'output/asset-improvement-20261030/column-base'
RESOURCE='models/props/collider/column-base-trial-v1';MAT='materials/collider/column-base-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((-960.,-500.,0.));UP=np.array((0.,0.,1.));AXES=np.eye(3)
ANCHORS=[(x,y) for x in (-29.,29.) for y in (-24.,-8.,8.,24.)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def signature(p,ps):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in ps))


def baseline():
    raw=K.Model();raw.box(ORIGIN+(-44,-44,0),ORIGIN+(44,44,8),'co_trim')
    expected=Counter(signature(p,[ps[0],ps[i],ps[i+1]]) for p,polys in raw.polygons.items()
                     for ps,n in polys for i in range(1,len(ps)-1))
    remaining=expected.copy();before=K.Model();context=K.Model();vs=[];uv=[];ns=[];paint=''
    source=ROOT/'Assets/models/maps/collider/collider_structure.obj'
    with source.open() as f:
        for line in f:
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
            elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('vn '):
                a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f ') and paint in ('co_trim','co_steel'):
                ids=[[int(v)-1 for v in s.split('/')] for s in line.split()[1:]]
                ps=[vs[v] for v,t,n in ids];key=signature(paint,ps)
                if remaining[key]:
                    remaining[key]-=1;target=before
                elif paint=='co_steel' and all(-998.01<=p[0]<=-921.99 and -538.01<=p[1]<=-461.99 and 7.999<=p[2]<=440.001 for p in ps):
                    target=context
                else:continue
                target.polygon(paint,[p-ORIGIN for p in ps],uv=[uv[t] for v,t,n in ids],normals=[ns[n] for v,t,n in ids])
    assert not +remaining and before.triangle_count()==12
    assert context.triangle_count()==36,context.triangle_count()
    M.configure(before);M.configure(context)
    return before,context,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
        'planOrigin':ORIGIN.tolist(),'exactMatchedTriangles':12,'copiedSavedGeometryUVsNormals':True,
        'unchangedActualColumnContextTriangles':36,'contextIsRenderOnly':True}


def block(m,p,size,paint='cb_edge',radius=.5,bevel=.12):
    O.round_block(m,np.asarray(p,float),size,paint,radius,bevel,segments=3)


def grout(m):
    # Recessed mortar bed: small real chips and a broken edge, not a perfect cube.
    rng=np.random.default_rng(301031);outline=O.outline(88,88,1.2,8);rings=[]
    for z,inset in ((0.,.05),(.55,0.),(2.5,.15),(3.05,.55)):
        ring=[]
        for i,p in enumerate(outline):
            n=K.normalise(p);chip=.08+.35*rng.random()
            if i%9==0:chip+=.34
            ring.append(np.array((*(p-n*(inset+chip)),z+(.03*rng.random() if z not in (0.,3.05) else 0))))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for i in range(len(a)):
            j=(i+1)%len(a);points=[a[i],a[j],b[j],b[i]]
            face(m,'cb_grout',points,(a[i]+a[j])*np.array((1,1,0)))
    for sign,ring,z in ((-1,rings[0],0.),(1,rings[-1],3.05)):
        center=np.array((0.,0.,z))
        for i in range(len(ring)):
            face(m,'cb_grout',[center,ring[i],ring[(i+1)%len(ring)]],UP*sign)


def hex_nut(m,c):
    c=np.asarray(c,float);outline=[];inside=[]
    for i in range(24):
        edge=i//4;t=(i%4)/4
        a=np.array((math.cos(math.tau*edge/6),math.sin(math.tau*edge/6)))
        b=np.array((math.cos(math.tau*(edge+1)/6),math.sin(math.tau*(edge+1)/6)))
        outline.append((a*(1-t)+b*t)*1.35)
        angle=math.atan2(outline[-1][1],outline[-1][0]);inside.append(np.array((math.cos(angle),math.sin(angle)))*.77)
    rings=[[c+np.array((*(p*scale),z)) for p in outline] for z,scale in ((0.,.90),(.14,1.),(1.10,1.),(1.24,.90))]
    for a,b in zip(rings,rings[1:]):
        for i in range(24):
            j=(i+1)%24;face(m,'cb_bolt',[a[i],a[j],b[j],b[i]],a[i]+a[j]-2*c)
    for sign,ring,z in ((-1,rings[0],0.),(1,rings[-1],1.24)):
        inner=[c+np.array((*p,z)) for p in inside]
        for i in range(24):
            j=(i+1)%24;face(m,'cb_bolt',[ring[i],ring[j],inner[j],inner[i]],UP*sign)
    # Bore remains genuinely open around the stud.
    for i in range(24):
        j=(i+1)%24;a=c+np.array((*inside[i],0));b=c+np.array((*inside[j],0))
        face(m,'cb_bolt',[a,b,b+(0,0,1.24),a+(0,0,1.24)],-(a+b-2*c))


def stud(m,x,y):
    c=np.array((x,y,8.))
    B.lathe(m,c,UP,[(.77,0),(1.78,0),(1.78,.22),(.77,.22),(.77,0)],'cb_metal',sides=32)
    hex_nut(m,c+(0,0,.25))
    # One continuous helical threaded surface, with analytic sampling normals.
    z0,z1=8.0,12.3;pitch=.23;steps=58;sides=20
    def point(z,a):
        phase=(z/pitch-a/math.tau)%1
        r=.68+.065*(1-abs(phase-.5)*2)
        return np.array((x+r*math.cos(a),y+r*math.sin(a),z))
    def normal(z,a):
        h=.0001
        return K.normalise(np.cross(point(z,a+h)-point(z,a-h),point(z+h,a)-point(z-h,a)))
    for i in range(steps):
        za=z0+(z1-z0)*i/steps;zb=z0+(z1-z0)*(i+1)/steps
        for j in range(sides):
            aa=math.tau*j/sides;ab=math.tau*(j+1)/sides
            coords=[(za,aa),(za,ab),(zb,ab),(zb,aa)]
            ns=[normal(z,a) for z,a in coords]
            face(m,'cb_bolt',[point(z,a) for z,a in coords],sum(ns),normals=ns)
    for sign,z in ((-1,z0),(1,z1)):
        face(m,'cb_bolt',[point(z,math.tau*j/sides) for j in range(sides)],UP*sign)


def weld(m,a,b,seed):
    a,b=np.asarray(a,float),np.asarray(b,float);axis=K.normalise(b-a);length=np.linalg.norm(b-a)
    u=K.normalise(np.cross(axis,UP if abs(axis[2])<.9 else (1,0,0)));v=np.cross(axis,u)
    count=max(2,int(math.ceil(length/.8)));rings=[];normals=[]
    for i in range(count+1):
        t=i/count;radius=.19*(1+.10*math.sin(i*2.2+seed)+.04*math.sin(i*5.3))
        center=a+(b-a)*t
        ns=[u*math.cos(j*math.tau/6)+v*math.sin(j*math.tau/6) for j in range(6)]
        rings.append([center+radius*n for n in ns]);normals.append(ns)
    for i in range(count):
        for j in range(6):
            k=(j+1)%6;ps=[rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]]
            ns=[normals[i][j],normals[i][k],normals[i+1][k],normals[i+1][j]]
            face(m,'cb_weld',ps,sum(ns),normals=ns)
    face(m,'cb_weld',rings[0],-axis);face(m,'cb_weld',rings[-1],axis)


def rib(m,points,normal,seed):
    points=[np.asarray(p,float) for p in points];n=np.asarray(normal,float)*.42
    a=[p-n for p in points];b=[p+n for p in points]
    face(m,'cb_edge',a,-n);face(m,'cb_edge',b,n)
    for i in range(3):
        j=(i+1)%3;ps=[a[i],a[j],b[j],b[i]];face(m,'cb_edge',ps,np.cross(ps[1]-ps[0],ps[2]-ps[0]))
    # Root and upright seams on both visible sides; the free diagonal edge is unwelded.
    for sign in (-1,1):
        weld(m,points[0]+n*sign,points[1]+n*sign,seed)
        weld(m,points[0]+n*sign,points[2]+n*sign,seed+1)


def candidate():
    m=K.Model();grout(m)
    plate=K.Model();block(plate,(0,0,5.5),(84,84,5.),'cb_plate',.85,.32)
    for i,(ps,n) in enumerate(plate.polygons['cb_plate']):
        top=abs(n[2])>.9;paint='cb_plate' if top else 'cb_edge'
        m.polygon(paint,ps,n,uv=[((p[0]+42)/84,(p[1]+42)/84) for p in ps] if top else None)
    for x,y in ANCHORS:stud(m,x,y)
    for y in (-29.99,29.99):weld(m,(-37.7,y,8.12),(37.7,y,8.12),int(y))
    for x in (-5.99,5.99):weld(m,(x,-29.7,8.12),(x,29.7,8.12),int(x))
    for x in (-23.,23.):
        for sign in (-1,1):rib(m,[(x,sign*29.99,8.1),(x,sign*14.,8.1),(x,sign*29.99,31.)],(1,0,0),int(x+sign))
    for sign in (-1,1):rib(m,[(sign*5.99,0,8.1),(sign*23.,0,8.1),(sign*5.99,0,27.)],(0,1,0),sign*4)
    # An attached identification tag sits flat on the exposed front margin.
    block(m,(0,-40.,8.04),(22.,2.5,.08),'cb_dark',.25,.02)
    face(m,'cb_label',[(-10.5,-41.0,8.085),(10.5,-41.,8.085),(10.5,-39.,8.085),(-10.5,-39.,8.085)],UP,
         uv=[(0,0),(1,0),(1,1),(0,1)])
    for paint in m.polygons:m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=12.
    return m


def materials():
    import ares_materials as AM
    MD.mkdir(parents=True,exist_ok=True);n=1024;rng=np.random.default_rng(301102)
    yy,xx=np.mgrid[:n,:n];x=xx/n;y=yy/n;fine=rng.normal(0,1,(n,n))
    grain=ndi.gaussian_filter(fine,.6,mode='wrap');grain/=grain.std();broad=ndi.gaussian_filter(fine,32,mode='wrap');broad/=broad.std()
    for name,base,rough,metal,height in (
        ('cb_edge',(58,70,73),.57,.05,.0008),('cb_metal',(132,139,138),.35,.90,.00018),
        ('cb_bolt',(73,76,70),.44,.80,.0004),('cb_dark',(28,33,33),.68,0,.0006),
        ('cb_weld',(76,81,76),.49,.79,.0012),('cb_grout',(131,128,115),.87,0,.015)):
        color=np.array(base)[None,None,:]*(1+.016*grain[...,None]+.03*broad[...,None])
        h=grain*height;roughness=np.clip(rough+.022*grain+.03*broad,.18,.97)
        if name=='cb_grout':
            pores=ndi.gaussian_filter(fine,2.1,mode='wrap');pores/=pores.std();h+=pores*.025
            color+=(pores[...,None]*7);color[pores>1.6]*=.72
        if name in ('cb_edge','cb_bolt','cb_weld'):
            pits=(grain>1.8)&(broad>.25);color[pits]*=.71;h[pits]-=.0025
        path=f'{MAT}/{name}'
        Image.fromarray(np.clip(color,0,255).astype('uint8')).save(MD/(name+'_color.png'))
        AM.BX.save_grey(MD/(name+'_rough.png'),roughness)
        AM.BX.save_normal(MD/(name+'_normal.png'),AM.normals(h,(n/12,n/12)))
        (MD/(name+'.vmat')).write_text(O.vmat(name,path+'_color.png',path+'_normal.png',path+'_rough.png',metal))
    # Unique plate surface: coating loss at exposed edges, fastener halos and weld heat marks.
    X=x*84-42;Y=y*84-42;edge=np.minimum(42-abs(X),42-abs(Y))
    noise=ndi.gaussian_filter(fine,1.4,mode='wrap');noise/=noise.std()
    chipped=np.clip((.85-edge+.22*noise)*2,0,1)
    grime=np.zeros_like(x);rust=np.zeros_like(x)
    for ax,ay in ANCHORS:
        r=np.hypot(X-ax,Y-ay);grime+=.38*np.exp(-((r-2.0)/1.0)**2)
        rust+=.32*np.exp(-((r-2.4)/.75)**2)*np.clip(.5+.25*broad,0,1)
    seam=np.minimum.reduce((abs(X-6),abs(X+6),abs(Y-30),abs(Y+30)))
    grime+=.30*np.exp(-seam/.70)
    scratch=Image.new('L',(n,n));d=ImageDraw.Draw(scratch)
    for _ in range(450):
        a,b=rng.uniform(0,n,2);length=rng.uniform(3,38)
        d.line((a,b,a+length,b+rng.normal(0,3)),fill=int(rng.uniform(25,150)),width=1)
    scratches=np.asarray(scratch)/255;chipped=np.clip(chipped+scratches*.3,0,1)
    color=np.array((56.,69.,74.))[None,None,:]*(1+.02*broad[...,None]+.011*grain[...,None])
    color=color*(1-chipped[...,None])+np.array((139.,143.,136.))*chipped[...,None]
    color*=1-np.clip(grime,0,.7)[...,None]
    color=color*(1-rust[...,None])+np.array((86.,53.,29.))*rust[...,None]
    rough=np.clip(.59+.018*broad+.16*grime-.22*chipped+.15*rust,.25,.94)
    metal=np.clip(.02+.85*chipped-.75*rust,0,.95)
    h=grain*.0009-chipped*.0045-scratches*.002
    Image.fromarray(np.clip(color,0,255).astype('uint8')).save(MD/'plate_color.png')
    AM.BX.save_grey(MD/'plate_rough.png',rough);AM.BX.save_grey(MD/'plate_metal.png',metal)
    AM.BX.save_normal(MD/'plate_normal.png',AM.normals(h,(n/84,n/84)))
    mat=O.vmat('cb_plate',f'{MAT}/plate_color.png',f'{MAT}/plate_normal.png',f'{MAT}/plate_rough.png')
    mat=mat.replace('    g_flMetalness "0.0"',f'    F_METALNESS_TEXTURE "1"\n    TextureMetalness "{MAT}/plate_metal.png"')
    assert 'TextureMetalness' in mat
    (MD/'cb_plate.vmat').write_text(mat)
    label=Image.new('RGB',(1536,160),(36,42,42));d=ImageDraw.Draw(label)
    d.text((768,58),'COLLIDER  /  COLUMN C-03',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',45),anchor='mm',fill=(171,178,164))
    d.text((768,115),'STRUCTURAL BASE   /   ANCHOR GROUP 08',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26),anchor='mm',fill=(119,130,124))
    label.save(MD/'label_color.png');(MD/'cb_label.vmat').write_text(O.vmat('cb_label',f'{MAT}/label_color.png',rough='[0.62 0.62 0.62 0]'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');parser.add_argument('--geometry-only',action='store_true');args=parser.parse_args()
    if DEST.exists():
        assert args.refine
        old=json.loads((OUT/'manifest.json').read_text())
        for path,h in old['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
    spec=importlib.util.spec_from_file_location('console_build',ROOT/'Sources/Collider/console-trial-v1/build.py')
    C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C);guards=C.protected()
    for folder in (ROOT/'Assets/models/props/collider/console-trial-v1',ROOT/'Assets/materials/collider/console-trial-v1'):
        guards.update({p.relative_to(ROOT).as_posix():sha(p) for p in folder.iterdir() if p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')})
    guards={p:h for p,h in guards.items() if '/column-base-trial-v1/' not in p}
    before,context,provenance=baseline();after=candidate()
    for model in (before,context):
        for path in model.material_overrides.values():
            matpath=ROOT/'Assets'/path;guards[path if path.startswith('Assets/') else 'Assets/'+path]=sha(matpath)
            for tex in re.findall(r'Texture\w+\s+"([^\"]+)"',matpath.read_text()):
                p=ROOT/'Assets'/tex
                if not tex.startswith('[') and p.is_file():guards['Assets/'+tex]=sha(p)
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    if not args.geometry_only:materials()
    variants={}
    for name,model in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),model,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,model)
        variants[name]={'triangles':model.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    ctx=OUT/'context';ctx.mkdir(exist_ok=True);K.write_obj(ctx/'context.obj',context,'context')
    (ctx/'materials.json').write_text(json.dumps({p+'.vmat':v for p,v in context.material_overrides.items()},indent=2)+'\n')
    for path,h in guards.items():assert sha(ROOT/path)==h,path
    result={'status':'candidate-only-not-installed','userApproved':False,'editorUsed':False,'engineCompilation':'pending',
        'baseline':provenance,'models':variants,'protectedSourceSHA256':guards,'originalRetained':True,
        'collisionUnchanged':True,'collisionShapes':0,'originalBaseEnvelopeInches':[88,88,8],
        'eightThreadedAnchors':True,'sixWeldedStiffeners':True,'contextMeshSHA256':sha(ctx/'context.obj'),
        'newDetails':['chipped grout perimeter','bevelled steel plate with localized coating loss',
            'eight threaded anchors with open washers and hexagonal nuts','six welded stiffeners connecting to the actual H-column',
            'continuous weld beads','bolt-centered oxidation and dirt','attached engraved identification plate'],
        'workload':{'priority':'idle','cpuAffinity':proc.cpu_affinity(),'BLASThreads':1}}
    for path in (OUT/'manifest.json',Path(__file__).parent/'candidate.json'):path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='protectedSourceSHA256'}))


if __name__=='__main__':main()
