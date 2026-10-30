"""Private actual-mesh review of one saved Collider shutoff valve."""
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import boxyard_map as B
import collider_services as S
import collider_map as M
import ares_materials as AM
import valve_surface as V
from belltower_furniture import bevel_box,face

OUT=ROOT/'output/asset-improvement-20261029/valve'
RESOURCE='models/props/collider/valve-trial-v1';MAT='materials/collider/valve-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((-1280.,280.,757.))
ROTATION=np.array(((0.,1.,0.),(-1.,0.,0.),(0.,0.,1.)))
UP=np.array((0.,0.,1.));FRONT=np.array((0.,-1.,0.));X=np.array((1.,0.,0.));C=np.array((0.,0.,13.))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def key(p,ps):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in ps))

def baseline():
    raw=K.Model();S.valve(raw,(-1280.,280.,770.),(1,0,0))
    remaining=Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in raw.polygons.items() for ps,n in polys for i in range(1,len(ps)-1))
    m=K.Model();vs=[];uv=[];ns=[];paint='';path=ROOT/'Assets/models/maps/collider/collider_detail.obj'
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f ') and paint in raw.polygons:
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            points=[vs[v] for v,t,n in ids];signature=key(paint,points)
            if remaining[signature]:
                remaining[signature]-=1
                m.polygon(paint,[ROTATION@(p-ORIGIN) for p in points],uv=[uv[t] for v,t,n in ids],normals=[ROTATION@ns[n] for v,t,n in ids])
    assert not +remaining and m.triangle_count()==678
    M.configure(m)
    return m,{'source':path.relative_to(ROOT).as_posix(),'sourceSHA256':sha(path),'planValveCenter':[-1280.,280.,770.],
        'exactMatchedTriangles':678,'copiedSavedGeometryUVsNormals':True}

def lathe(m,base,axis,profile,paint,sides=40,cap=None,turn=0.):
    B.lathe(m,base,axis,profile,paint,sides=sides,cap=cap,turn=turn)

def ring(m,at,axis,inside,outside,thickness,paint,sides=40):
    lathe(m,at,axis,[(inside,-thickness/2),(outside,-thickness/2),(outside,thickness/2),
        (inside,thickness/2),(inside,-thickness/2)],paint,sides)

def cast_shell(m,at,axis,heights,radii,paint,sides=48,steps=24,cap=False):
    """Continuous cast curvature with analytic profile normals, including shoulders."""
    at=np.array(at,float);axis=K.normalise(np.array(axis,float))
    u=K.normalise(np.cross(axis,UP));v=np.cross(axis,u)
    curve=PchipInterpolator(heights,radii);derivative=curve.derivative()
    hs=np.linspace(heights[0],heights[-1],steps+1)
    def surface(h,a):
        radial=u*math.cos(a)+v*math.sin(a)
        r=float(curve(h))+V.cast_offset(h,a,heights[0],heights[-1])
        return at+axis*h+radial*r
    rings=[]
    for h in hs:
        ring=[]
        for i in range(sides):
            a=i*math.tau/sides
            tangent=surface(h,a+.0001)-surface(h,a-.0001)
            along=surface(h+.0001,a)-surface(h-.0001,a)
            ring.append((surface(h,a),K.normalise(np.cross(tangent,along))))
        rings.append(ring)
    for band,(bottom,top) in enumerate(zip(rings,rings[1:])):
        for i in range(sides):
            j=(i+1)%sides;items=(bottom[i],bottom[j],top[j],top[i])
            uv=[(band/steps,i/sides),(band/steps,(i+1)/sides),((band+1)/steps,(i+1)/sides),((band+1)/steps,i/sides)]
            m.polygon(paint,[p for p,n in items],uv=uv,normals=[n for p,n in items])
    if cap:face(m,'vv_body',[p for p,n in rings[-1]],axis)

def bolt(m,at,axis,r=.7):
    at=np.array(at,float);axis=np.array(axis,float)
    ring(m,at,axis,r*.55,r*1.35,.18,'vv_metal',24)
    turn=math.sin(float(np.dot(at,(1.31,2.57,3.11))))*.52
    lathe(m,at,axis,[(r*.95,.08),(r,.16),(r,.75),(r*.85,.88)],'vv_bolt',6,'vv_bolt',turn)
    lathe(m,at,axis,[(r*.48,.86),(r*.48,1.15)],'vv_metal',12,'vv_metal')

def wheel(m):
    centre=np.array((0.,-25.,13.));major=11.05;minor=1.18;around=64;section=16
    def point(i,j):
        a=i*math.tau/around;b=j*math.tau/section
        radial=np.array((math.cos(a),0,math.sin(a)));normal=radial*math.cos(b)+FRONT*math.sin(b)
        return centre+radial*major+normal*minor,normal
    for i in range(around):
        for j in range(section):
            ij=((i,j),(i+1,j),(i+1,j+1),(i,j+1));values=[point(a,b) for a,b in ij]
            m.polygon('vv_wheel',[p for p,n in values],uv=[(a/around,b/section) for a,b in ij],normals=[n for p,n in values])
    for k in range(4):
        a=k*math.tau/4+.24
        points=[centre+np.array((r*math.cos(a+b),0,r*math.sin(a+b))) for r,b in ((2.,-.20),(6.2,-.10),(10.8,0.))]
        S.pipe_run(m,points,.80,'vv_red',12,2.)
    lathe(m,centre,FRONT,[(2.8,-1.1),(3.,-.8),(3.,.7),(2.7,1.1)],'vv_red',40,'vv_red')
    ring(m,centre+FRONT*1.15,FRONT,.65,1.65,.16,'vv_metal',32)
    lathe(m,centre+FRONT*1.3,FRONT,[(1.05,0),(1.05,.6),(.9,.75)],'vv_bolt',6,'vv_bolt')

def candidate():
    m=K.Model()
    # Cast pressure body and stepped, bolted pipe flanges.
    cast_shell(m,C,X,[-13.3,-10.,-5.,0.,5.,10.,13.3],[6.5,8.1,10.1,10.6,10.1,8.1,6.5],'vv_cast')
    # Inward-facing bore closes the casing interior between the flange throats.
    # The descending profile gives this cylinder proper inward normals.
    lathe(m,C,X,[(5.,11.9),(5.,-11.9)],'vv_bore',48)
    for side in (-1,1):
        at=C+X*side*13.4;axis=X*side
        lathe(m,at,axis,[(5.,-1.5),(11.7,-1.5),(12.5,-.7),(12.5,2.4),(11.8,3.2),(5.,3.2),(5.,-1.5)],['vv_flange','vv_body','vv_body','vv_body','vv_flange','vv_bore'],48)
        ring(m,C+X*side*12.,axis,6.5,11.7,.25,'vv_rubber',48)
        ring(m,C+X*side*16.64,axis,5.,8.2,.20,'vv_metal',48)
        for r in (6.4,7.3):ring(m,C+X*side*16.77,axis,r,r+.08,.04,'vv_bolt',48)
        for k in range(8):
            a=k*math.tau/8+math.pi/8
            bolt(m,C+X*side*16.7+np.array((0,math.cos(a)*10.4,math.sin(a)*10.4)),axis,.72)
    # A separate bonnet, gasket seam, packing collar and exposed rising stem.
    cast_shell(m,C+FRONT*5.0,FRONT,[0.,.8,2.4,4.3,6.2],[8.1,8.1,7.2,6.8,5.7],'vv_bonnet',40,16,True)
    ring(m,C+FRONT*11.35,FRONT,1.1,5.95,.32,'vv_rubber',40)
    lathe(m,C+FRONT*11.6,FRONT,[(1.12,0),(6.2,0),(6.5,.35),(6.5,1.05),(5.2,1.45),(4.7,3.0),(1.12,3.0),(1.12,0)],'vv_body',40)
    for k in range(4):
        a=k*math.tau/4+math.pi/4
        bolt(m,C+FRONT*12.7+np.array((math.cos(a)*5.1,0,math.sin(a)*5.1)),FRONT,.58)
    lathe(m,C+FRONT*14.1,FRONT,[(1.08,0),(1.08,11.9)],'vv_stem',32,'vv_stem')
    # Real helical thread rather than a stack of unrelated flat rings.
    thread=[C+FRONT*(15.5+t*8.5)+np.array((1.13*math.cos(t*math.tau*12),0,1.13*math.sin(t*math.tau*12))) for t in np.linspace(0,1,193)]
    S.pipe_run(m,thread,.105,'vv_stem',6,0)
    wheel(m)
    # Small identification plate on the casting, with an actual raised mounting pad.
    bevel_box(m,(6.2,-8.9,9.7),np.eye(3),(5.6,.7,3.0),'vv_body',.18)
    face(m,'vv_label',[(3.6,-9.27,8.4),(8.8,-9.27,8.4),(8.8,-9.27,11.0),(3.6,-9.27,11.0)],FRONT,uv=[(0,0),(1,0),(1,1),(0,1)])
    for x in (3.85,8.55):
        for z in (8.65,10.75):
            lathe(m,(x,-9.3,z),FRONT,[(.13,0),(.13,.06)],'vv_bolt',10,'vv_bolt')
    V.finish_mesh(m)
    for paint in m.polygons:
        m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=8.
    return m

def write_material(name,color,normal=None,rough=None,metal=0):
    metal_line=f'    TextureMetalness "{metal}"' if isinstance(metal,str) else f'    g_flMetalness "{metal}"'
    (MD/(name+'.vmat')).write_text('\n'.join(['"Layer0"','{','    shader "shaders/complex.shader"','    F_SPECULAR "1"',
        f'    TextureColor "{color}"',f'    TextureNormal "{normal or "materials/default/default_normal.tga"}"',
        f'    TextureRoughness "{rough or "[0.6 0.6 0.6 0]"}"','    TextureAmbientOcclusion "materials/default/default_ao.tga"',
        metal_line,'    g_flModelTintAmount "1"','    g_flRoughnessScaleFactor "1"','}'])+'\n')

def texture_set(name,color,height,rough,tile=(8.,8.)):
    h,w=height.shape
    Image.fromarray(np.clip(color,0,255).astype(np.uint8)).save(MD/(name+'_color.png'))
    AM.BX.save_normal(MD/(name+'_normal.png'),AM.normals(height,(w/tile[0],h/tile[1])))
    AM.BX.save_grey(MD/(name+'_rough.png'),np.clip(rough,0,1))
    return tuple(f'{MAT}/{name}_{suffix}.png' for suffix in ('color','normal','rough'))

def materials():
    MD.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(291023)
    h=w=1024;noise=rng.normal(0,1,(h,w));cast=gaussian_filter(noise,1.5,mode='wrap');cast/=cast.std()
    broad=gaussian_filter(noise,34,mode='wrap');broad/=broad.std()
    for name,base in (('vv_body',(52.,68.,74.)),('vv_red',(118.,33.,26.))):
        color=np.array(base)[None,None,:]*(1+.025*cast[...,None]+.018*broad[...,None])
        maps=texture_set(name,color,.0016*cast+.00025*noise,.65+.025*cast+.012*broad)
        write_material(name,*maps,metal=.04)
    # The handwheel has an explicit UV unwrap, with intermittent grip wear.
    h,w=512,1024;yy,xx=np.mgrid[:h,:w];v=yy/h;noise=rng.normal(0,1,(h,w))
    patches=gaussian_filter(noise,7,mode='wrap');patches/=patches.std()
    fine=gaussian_filter(noise,.8,mode='wrap');fine/=fine.std()
    shoulder=np.exp(-((v-.16)/.055)**2)+.6*np.exp(-(np.minimum(v,1-v)/.035)**2)
    wear=np.clip((patches-.95)*1.8,0,1)*np.clip(shoulder,0,1)
    base=np.array((118.,33.,26.))[None,None,:]*(1+.018*fine[...,None])
    color=base*(1-wear[...,None])+np.array((86.,82.,75.))[None,None,:]*wear[...,None]
    maps=texture_set('vv_wheel',color,.0007*fine,.64+.02*fine-.08*wear,(math.tau*11.05,math.tau*1.18))
    write_material('vv_wheel',*maps,metal=.05)
    write_material('vv_metal','[0.27 0.29 0.30 1]',rough='[0.36 0.36 0.36 0]',metal=.88)
    write_material('vv_bolt','[0.13 0.15 0.16 1]',rough='[0.46 0.46 0.46 0]',metal=.75)
    write_material('vv_rubber','[0.015 0.018 0.019 1]',rough='[0.84 0.84 0.84 0]')
    label=Image.new('RGB',(512,256),(178,180,171));draw=ImageDraw.Draw(label)
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',44)
    draw.text((256,70),'HV-07',font=font,anchor='mm',fill=(31,36,36))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27)
    draw.text((256,140),'COOLING INLET',font=font,anchor='mm',fill=(42,47,47))
    draw.text((256,194),'OPEN  /  CLOSE',font=font,anchor='mm',fill=(42,47,47))
    label.save(MD/'label.png');write_material('vv_label',f'{MAT}/label.png',metal=.12)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');args=parser.parse_args()
    if DEST.exists():
        assert args.refine,'Candidate already exists'
        old=json.loads((OUT/'manifest.json').read_text())
        for p,h in old['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p
        for n,d in old['models'].items():assert sha(DEST/(n+'.obj'))==d['meshSHA256']
    guards={}
    for n in ('structure','detail','machine','glass'):
        for ext in ('.obj','.mtl','.vmdl'):
            p=ROOT/'Assets/models/maps/collider'/('collider_'+n+ext)
            guards[p.relative_to(ROOT).as_posix()]=sha(p)
    p=ROOT/'Assets/scenes/maps/Collider/collider.scene';guards[p.relative_to(ROOT).as_posix()]=sha(p)
    before,provenance=baseline();after=candidate();materials();surface_stats=V.create_surfaces(MD,MAT,AM,write_material)
    DEST.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    models={}
    for name,m in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),m,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,m)
        models[name]={'triangles':m.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    for p,h in guards.items():assert sha(ROOT/p)==h,p
    result={'status':'candidate-only-not-installed','editorUsed':False,'engineCompilation':'pending','baseline':provenance,
        'models':models,'protectedSourceSHA256':guards,'authoredCollisionShapes':0,'caption':'Matched offline renders of the actual meshes',
        'revision':'surface-v2','surfaceStatistics':surface_stats,'previousProposal':'revisions/smooth-v1'}
    for p in (OUT/'manifest.json',Path(__file__).parent/'candidate.json'):p.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='protectedSourceSHA256'}))

if __name__=='__main__':main()
