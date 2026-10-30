"""Review candidate for one actual saved Collider wall display."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import sys
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import boxyard_map as B
import collider_map as M
import collider_services as S
from belltower_furniture import bevel_box,face

OUT=ROOT/'output/asset-improvement-20261029/monitor'
RESOURCE='models/props/collider/monitor-trial-v1';MAT='materials/collider/monitor-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
CENTER=np.array((1880.,-190.,381.));BOTTOM=345.5
UP=np.array((0.,0.,1.));FRONT=np.array((0.,-1.,0.));AXES=np.eye(3)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def signature(paint,points):
    return paint,tuple(sorted(tuple(round(float(v),3) for v in p) for p in points))


def local(p):return np.array((-(p[1]-CENTER[1]),p[0]-CENTER[0],p[2]-BOTTOM))
def local_normal(n):return np.array((-n[1],n[0],n[2]))


def baseline():
    raw=K.Model();M.monitor(raw,CENTER,(-1,0),112,66,0)
    expected=Counter(signature(p,[ps[0],ps[i],ps[i+1]]) for p,polys in raw.polygons.items()
        for ps,n in polys for i in range(1,len(ps)-1))
    remaining=expected.copy();m=K.Model();positions=[];uv=[];normals=[];paint=''
    source=ROOT/'Assets/models/maps/collider/collider_structure.obj'
    for line in source.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);positions.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f ') and paint in ('co_case','co_screens','co_beam'):
            ids=[[int(v)-1 for v in token.split('/')] for token in line.split()[1:]]
            points=[positions[v] for v,t,n in ids];key=signature(paint,points)
            if remaining[key]:
                remaining[key]-=1;m.polygon(paint,[local(p) for p in points],
                    uv=[uv[t] for v,t,n in ids],normals=[local_normal(normals[n]) for v,t,n in ids])
    assert not +remaining and m.triangle_count()==26
    M.configure(m)
    return m,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
        'planCenter':CENTER.tolist(),'exactMatchedTriangles':26,'copiedSavedGeometryUVsNormals':True}


def rect(width,height,radius,y,inset=0):
    # Counterclockwise X/Z perimeter, front normal -Y.
    w=width/2;z0=inset;z1=inset+height;points=[]
    for cx,cz,start in ((w-radius,z0+radius,-90),(w-radius,z1-radius,0),
            (-w+radius,z1-radius,90),(-w+radius,z0+radius,180)):
        for angle in np.linspace(start,start+90,7,endpoint=False):
            a=math.radians(angle);points.append(np.array((cx+radius*math.cos(a),y,cz+radius*math.sin(a))))
    return points


def band(m,a,b,paint):
    for i in range(len(a)):
        j=(i+1)%len(a)
        points=[a[i],a[j],b[j],b[i]]
        m.polygon(paint,points)


def block(m,center,size,paint='mm_shell',bevel=.12):
    bevel_box(m,np.array(center,float),AXES,np.array(size,float),paint,bevel)


def tube(m,a,b,r,paint='mm_metal',sides=16):
    a,b=np.array(a,float),np.array(b,float)
    B.lathe(m,a,b-a,[(r,0),(r,float(np.linalg.norm(b-a)))],paint,sides=sides,cap=paint)


def screw(m,at,normal=(0,-1,0),r=.22):
    at=np.array(at,float);normal=np.array(normal,float)
    B.lathe(m,at,normal,[(r,0),(r,.08),(r*.78,.15)],'mm_metal',sides=12,cap='mm_metal')


def candidate():
    m=K.Model()
    outer=rect(117,71,2.4,-.05);front=rect(116.2,70.2,2.15,-.42,.4)
    inner=rect(112.8,66.8,1.05,-.42,2.1);gasket=rect(112.35,66.35,.95,-.20,2.325)
    active=rect(112.,66.,.85,.13,2.5)
    rear=rect(114.,68.,2.0,3.7,1.5)
    band(m,outer,front,'mm_edge');band(m,front,inner,'mm_shell')
    band(m,inner,gasket,'mm_rubber');band(m,gasket,active,'mm_edge')
    band(m,rear,outer,'mm_shell')
    band(m,rect(110.,64.,.4,3.92,3.5),rear,'mm_edge')
    # Preserve the exact existing screen atlas quadrant and active image scale.
    uv=[((p[0]+56)/112*.5,.5+(p[2]-2.5)/66*.5) for p in active]
    face(m,'co_screens',active,FRONT,uv=uv)
    # Opaque display electronics sit behind the glass, inside the vent cavity.
    block(m,(0,2.8,35.5),(110.5,.16,64.5),'mm_shell',.04)
    # Rear cover sections leave genuine open cooling slots.
    for x0,x1 in ((-55,-42),(-34,34),(42,55)):
        block(m,((x0+x1)/2,3.65,35.5),(x1-x0,.5,64.),'mm_shell',.18)
    for side in (-1,1):
        for z in np.arange(5.,67.,2.2):
            block(m,(side*38,3.8,z),(8.,.45,.62),'mm_edge',.13)
    for x in (-52.,52.):
        for z in (5.,35.5,66.):screw(m,(x,4.,z),(0,1,0),.22)
    # Replace the glowing block with small functional operator controls.
    for x in (35.,39.,43.,47.,51.):
        B.lathe(m,(x,-.44,1.25),FRONT,[(.58,0),(.58,.10),(.45,.22)],'mm_rubber',sides=20,cap='mm_rubber')
    B.lathe(m,(55.3,-.45,1.25),FRONT,[(.22,0),(.22,.07)],'mm_led',sides=16,cap='mm_led')
    face(m,'mm_label',[(-51,-.435,.7),(-23,-.435,.7),(-23,-.435,1.75),(-51,-.435,1.75)],
        FRONT,uv=[(0,0),(1,0),(1,1),(0,1)])
    # Folded steel wall plate and two tilt arms connect to the existing rear wall.
    block(m,(0,19.45,35.5),(32.,.9,35.),'mm_mount',.35)
    for x in (-13.,13.):
        for z in (20.5,50.5):screw(m,(x,18.92,z),FRONT,.5)
    for x in (-18.,18.):
        block(m,(x,4.2,35.5),(3.,1.4,31.),'mm_mount',.3)
        for z in (24.,47.):
            # Two independent gusseted links, with a real pivot spindle.
            from belltower_furniture import beam
            beam(m,(x,5.,z),(x,18.8,35.5),(1.6,2.4),'mm_mount',.22)
            tube(m,(x-2.1,5.,z),(x+2.1,5.,z),.72,'mm_metal',20)
        for z in (21.,50.):screw(m,(x,3.38,z),FRONT,.35)
    # Power connector, strain relief and a routed cable; all behind the display.
    block(m,(36.,3.9,6.),(10.,1.,5.),'mm_mount',.25)
    tube(m,(36.,4.3,5.),(36.,6.0,5.),.65,'mm_rubber',16)
    S.pipe_run(m,[(36.,6.,5.),(36.,6.,-4.),(36.,12.,-7.),(36.,19.0,-4.),(36.,19.0,2.)],
        .38,'mm_rubber',12,3.)
    # Terminate the service loop in a sealed box flush with the existing wall.
    block(m,(36.,19.25,5.5),(6.,1.5,7.),'mm_mount',.25)
    B.lathe(m,(36.,19.,2.),(0,0,-1),[(.65,0),(.65,.35),(.48,.65)],
        'mm_rubber',sides=16,cap='mm_rubber')
    for x in (34.,38.):
        for z in (3.2,7.8):screw(m,(x,18.45,z),FRONT,.18)
    for x in (-39.,39.):screw(m,(x,-.045,69.1),FRONT,.18)
    for paint in m.polygons:
        m.material_overrides[paint]=f'{MAT}/{paint}.vmat' if paint.startswith('mm_') else f'materials/collider/{paint}.vmat'
        m.tile_overrides[paint]=32.
    return m


def materials():
    MD.mkdir(parents=True,exist_ok=True)
    image=Image.new('RGB',(2048,128),(44,49,53));draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',68)
    draw.text((38,20),'CONTROL DISPLAY     /     C14-02',font=font,fill=(161,169,171))
    image.save(MD/'label.png')
    specs={'mm_shell':('[0.025 0.031 0.035 1]',.64,.12),
        'mm_edge':('[0.045 0.053 0.057 1]',.43,.24),'mm_rubber':('[0.009 0.011 0.012 1]',.8,0),
        'mm_mount':('[0.065 0.078 0.085 1]',.62,.45),'mm_metal':('[0.34 0.37 0.39 1]',.38,.85),
        'mm_led':('[0.09 0.42 0.24 1]',.32,0),'mm_label':(f'{MAT}/label.png',.67,0)}
    for name,(color,rough,metal) in specs.items():
        text='\n'.join(['"Layer0"','{','    shader "shaders/complex.shader"','    F_SPECULAR "1"',
            f'    TextureColor "{color}"','    TextureNormal "materials/default/default_normal.tga"',
            f'    TextureRoughness "[{rough} {rough} {rough} 0]"','    TextureAmbientOcclusion "materials/default/default_ao.tga"',
            f'    g_flMetalness "{metal}"','    g_flModelTintAmount "1"','    g_flRoughnessScaleFactor "1"','}'])+'\n'
        (MD/(name+'.vmat')).write_text(text)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');args=parser.parse_args()
    if DEST.exists() and any(DEST.iterdir()):
        assert args.refine,'Use --refine for this task-owned candidate'
        old=json.loads((OUT/'manifest.json').read_text())
        for name,record in old['models'].items():assert sha(DEST/(name+'.obj'))==record['meshSHA256']
        for p,h in old['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    paths=[ROOT/'Assets/models/maps/collider'/f'collider_{name}{ext}' for name in ('structure','detail') for ext in ('.obj','.mtl','.vmdl')]
    paths.append(ROOT/'Assets/scenes/maps/Collider/collider.scene')
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
    before,provenance=baseline();after=candidate();materials();models={}
    for name,m in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),m,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,m)
        models[name]={'triangles':m.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    for p,h in guards.items():assert sha(ROOT/p)==h,p
    result={'status':'candidate-only-not-installed','editorUsed':False,'engineCompilation':'pending','baseline':provenance,
        'models':models,'protectedSourceSHA256':guards,'screenAtlasAndActiveImageUnchanged':True,
        'authoredCollisionShapes':0,'caption':'Actual exported meshes; matched offline renders'}
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'candidate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
