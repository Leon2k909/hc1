"""A reversible equipment-case candidate; no existing game asset is replaced."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import re
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import boxyard_map as B
import collider_map as M
import collider_detail_geometry as D
from belltower_furniture import bevel_box, face

OUT=ROOT/'output/asset-improvement-20261029/equipment-case'
RESOURCE='models/props/collider/equipment-case-trial-v1'
MAT='materials/collider/equipment-case-trial-v1'
DEST=ROOT/'Assets'/RESOURCE
MD=ROOT/'Assets'/MAT
UP=np.array((0.,0.,1.)); AXES=np.eye(3)
ORIGIN=np.array((-1150.,-350.,0.))


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def signature(paint,points):
    return paint,tuple(sorted(tuple(round(float(x),3) for x in p) for p in points))


def baseline():
    expected_model=K.Model()
    D.hardcase(expected_model,*ORIGIN,100,56,65,0,label=M.sign)
    expected=Counter(signature(paint,[points[0],points[i],points[i+1]])
        for paint,polygons in expected_model.polygons.items() for points,normal in polygons for i in range(1,len(points)-1))
    remaining=expected.copy()
    model=K.Model(); vertices=[];uvs=[];normals=[];paint='';spatial_body=0;matched=0
    bounds=np.array([p for polygons in expected_model.polygons.values() for ps,n in polygons for p in ps])
    lower,upper=bounds.min(0)-.002,bounds.max(0)+.002
    source=ROOT/'Assets/models/maps/collider/collider_detail.obj'
    for line in source.read_text(encoding='utf-8').splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vertices.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uvs.append(np.array(list(map(float,line.split()[1:]))))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);normals.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            indices=[[int(v)-1 for v in p.split('/')] for p in line.split()[1:]]
            points=[vertices[v] for v,t,n in indices]
            key=signature(paint,points)
            body=paint=='co_case' and np.all(np.array(points)>=lower) and np.all(np.array(points)<=upper)
            if remaining[key] or body:
                if remaining[key]:remaining[key]-=1;matched+=1
                if body:spatial_body+=1
                model.polygon(paint,[p-ORIGIN for p in points],
                    uv=[uvs[t] for v,t,n in indices],normals=[normals[n] for v,t,n in indices])
    # Saved body geometry differs from the current generator. Copy
    # those original body faces spatially; every hardware/label face must match.
    assert all(p=='co_case' for p,ps in +remaining), 'Hardware changed outside the isolated source case'
    assert spatial_body==88, ('Unexpected original body partition',spatial_body)
    M.configure(model)
    model.box((-50,-28,3),(50,28,65),None,'plastic')
    return model, {'source':source.relative_to(ROOT).as_posix(),'sha256':sha(source),
        'sourceOriginPlan':ORIGIN.tolist(),'exactHardwareTriangleMatches':matched,
        'originalBodyTrianglesCopied':spatial_body,'installedBodyDiffersFromCurrentGenerator':bool(+remaining),
        'copiedInstalledGeometryUVsAndNormals':True}


def block(m,center,size,paint='tc_steel',bevel=.15):
    bevel_box(m,np.array(center),AXES,np.array(size),paint,bevel)


def tube(m,a,b,r,paint='tc_steel',sides=16):
    a,b=np.array(a),np.array(b)
    direction=b-a
    B.lathe(m,a,direction,[(r,0),(r,float(np.linalg.norm(direction)))],paint,sides=sides,cap=paint)


def rivet(m,at,normal,r=.26):
    normal=np.array(normal,float);at=np.array(at,float)
    B.lathe(m,at,normal,[(r,0),(r,.045),(r*.83,.12),(r*.4,.17)],'tc_steel',sides=10,cap='tc_steel')


def panel(m,normal,depth,rect,holes=()):
    """Actual cut face and closed recessed wells; no coplanar dark overlays."""
    normal=np.array(normal,float);right=np.cross(normal,UP)
    u0,u1,z0,z1=rect
    us=sorted({u0,u1,*[v for h in holes for v in h[:2]]})
    zs=sorted({z0,z1,*[v for h in holes for v in h[2:]]})
    def p(u,d,z):return right*u+normal*d+UP*z
    for ua,ub in zip(us,us[1:]):
        for za,zb in zip(zs,zs[1:]):
            if not (u0<=ua<ub<=u1 and z0<=za<zb<=z1):continue
            if any(h[0]<(ua+ub)/2<h[1] and h[2]<(za+zb)/2<h[3] for h in holes):continue
            face(m,'tc_panel',[p(ua,depth,za),p(ub,depth,za),p(ub,depth,zb),p(ua,depth,zb)],normal)
    for ua,ub,za,zb in holes:
        well_depth=depth-1.45
        face(m,'tc_dark',[p(ua,well_depth,za),p(ub,well_depth,za),p(ub,well_depth,zb),p(ua,well_depth,zb)],normal)
        for a,b,n in (((ua,za),(ub,za),UP),((ub,za),(ub,zb),-right),
                ((ub,zb),(ua,zb),-UP),((ua,zb),(ua,za),right)):
            face(m,'tc_steel',[p(*a[:1],depth,a[1]),p(*b[:1],depth,b[1]),
                p(b[0],well_depth,b[1]),p(a[0],well_depth,a[1])],n)


def handle(m,normal,depth,width=22):
    normal=np.array(normal,float);right=np.cross(normal,UP)
    def p(u,d,z):return right*u+normal*d+UP*z
    half=width/2-3.2
    for side in (-1,1):
        c=p(side*half,depth-.55,34.5)
        # Hinge barrels turn on the same horizontal axis as the folding handle.
        B.lathe(m,c-right*.85,right,[(.86,0),(.86,1.7)],'tc_steel',sides=20,cap='tc_steel')
        rivet(m,p(side*half,depth-1.15,36.0),normal,.22)
    corners=[(-half,34.5),(-half,28.8),(-half+1.0,27.7),
        (half-1.0,27.7),(half,28.8),(half,34.5)]
    for (ua,za),(ub,zb) in zip(corners,corners[1:]):
        tube(m,p(ua,depth+.25,za),p(ub,depth+.25,zb),.43)
    tube(m,p(-half+1.5,depth+.25,27.7),p(half-1.5,depth+.25,27.7),.62,'tc_rubber',24)


def latch(m,x):
    """Draw latch inside its real cut pocket, bridging the lid seam."""
    y=-27.5
    block(m,(x,y+1.1,46.5),(6.2,.5,8.4),'tc_dark',.45)
    block(m,(x,y+.4,48.4),(2.2,.65,5.1),'tc_steel',.25)
    # A raised butterfly cam, tapered side wings and a central pivot.
    for s in (-1,1):
        face(m,'tc_steel',[(x+s*.45,y-.25,46.6),(x+s*2.9,y-.05,47.4),
            (x+s*2.9,y-.05,49.7),(x+s*.45,y-.25,49.2)],(0,-1,0))
    tube(m,(x,y+.2,48.1),(x,y-.65,48.1),.55,'tc_edge',16)
    # Wire bail and strike pull down on the lid extrusion.
    for dx in (-1.25,1.25):tube(m,(x+dx,y-.15,49.6),(x+dx,y-.15,56.4),.20,'tc_steel',12)
    tube(m,(x-1.25,y-.15,56.4),(x+1.25,y-.15,56.4),.20,'tc_steel',12)
    block(m,(x,y-.03,57.25),(4.4,.55,1.8),'tc_steel',.22)
    for dx in (-1.3,1.3):rivet(m,(x+dx,y-.33,57.25),(0,-1,0),.2)


def candidate():
    m=K.Model()
    m.box((-50,-28,3),(50,28,65),None,'plastic')
    handle_hole=(-13,13,24.5,37.5)
    latch_holes=((-38.8,-29.2,40.7,51.8),(29.2,38.8,40.7,51.8))
    for sy in (-1,1):
        holes=(handle_hole,*latch_holes) if sy<0 else (handle_hole,)
        panel(m,(0,sy,0),27.5,(-47.8,47.8,7.0,51.8),holes)
        panel(m,(0,sy,0),27.5,(-47.8,47.8,57.1,63.2))
        handle(m,(0,sy,0),27.5)
        for x in np.linspace(-43.5,43.5,8):
            for zz in (6.4,52.8,56.25,64.1):rivet(m,(x,sy*28.0,zz),(0,sy,0),.24)
        for x in (-49.,49.):
            block(m,(x,sy*26.9,35.0),(1.8,1.9,59.5),'tc_steel',.22)
        for zz,thick in ((5.7,2.2),(52.9,1.6),(56.1,1.5),(64.2,1.7)):
            block(m,(0,sy*27.6,zz),(98.3,1.25,thick),'tc_steel',.19)
    for sx in (-1,1):
        panel(m,(sx,0,0),49.,(-25.8,25.8,7.0,51.8),((-11.,11.,24.5,37.5),))
        panel(m,(sx,0,0),49.,(-25.8,25.8,57.1,63.2))
        handle(m,(sx,0,0),49.,18.)
        for zz,thick in ((5.7,2.2),(52.9,1.6),(56.1,1.5),(64.2,1.7)):
            block(m,(sx*49.,0,zz),(1.3,53.8,thick),'tc_steel',.19)
        for yy in np.linspace(-22.,22.,5):
            for zz in (6.2,52.8,56.2,64.1):rivet(m,(sx*49.72,yy,zz),(sx,0,0),.24)
    # Continuous gasket and two shells; the top remains a separate lid.
    block(m,(0,0,54.4),(98.3,54.5,1.2),'tc_rubber',.30)
    block(m,(0,0,3.4),(97.,53.,1.3),'tc_dark',.4)
    block(m,(0,0,63.7),(97.,53.,1.0),'tc_panel',.35)
    for yy in (-18.5,18.5):
        block(m,(0,yy,64.6),(86.,3.3,1.0),'tc_dark',.38)
        block(m,(0,yy,65.2),(83.,2.65,.45),'tc_rubber',.16)
    # Formed protective corners. Edges have a separate polished contact finish.
    for sx in (-1,1):
        for sy in (-1,1):
            block(m,(sx*46.3,sy*24.1,3.0),(8.0,8.0,6.0),'tc_rubber',1.3)
            for zz in (9.4,61.5):
                block(m,(sx*46.4,sy*27.9,zz),(7.6,1.2,6.6),'tc_steel',.65)
                block(m,(sx*49.5,sy*24.3,zz),(1.2,7.4,6.6),'tc_steel',.65)
                for dx in (0,3.0):rivet(m,(sx*(43.4+dx),sy*28.54,zz),(0,sy,0),.26)
                rivet(m,(sx*50.14,sy*23.0,zz),(sx,0,0),.26)
            block(m,(sx*46.8,sy*24.8,65.05),(6.5,5.7,1.6),'tc_edge',.6)
    for x in (-34.,34.):
        latch(m,x)
        # Rear piano hinge barrels, alternating knuckles and fixing leaves.
        for offset in (-2.25,-.75,.75,2.25):
            tube(m,(x+offset-.65,28.2,54.6),(x+offset+.65,28.2,54.6),.64,'tc_steel',16)
        for zz in (52.1,57.0):
            block(m,(x,27.86,zz),(6.3,.45,3.1),'tc_steel',.25)
            for dx in (-2.0,2.0):rivet(m,(x+dx,28.16,zz),(0,1,0),.23)
    # A small metal asset plate, recessed screw heads and printed serial label.
    block(m,(20.,-27.72,17.5),(22.4,.42,8.3),'tc_steel',.3)
    face(m,'tc_label',[(9.3,-27.96,13.7),(30.7,-27.96,13.7),
        (30.7,-27.96,21.3),(9.3,-27.96,21.3)],(0,-1,0),uv=[(0,0),(1,0),(1,1),(0,1)])
    for x in (9.5,30.5):
        for zz in (14.1,20.9):rivet(m,(x,-28.03,zz),(0,-1,0),.17)
    for paint in m.polygons:
        m.material_overrides[paint]=f'{MAT}/{paint}.vmat'
        m.tile_overrides[paint]=48. if paint=='tc_panel' else 16.
    return m


def materials():
    MD.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(291029)
    n=1024;grain=rng.normal(0,1,(n,n))
    colour=np.clip(np.array([61.,78.,82.])[None,None,:]+grain[:,:,None]*1.0,0,255).astype(np.uint8)
    rough=np.clip(.64+grain*.012,.1,1)
    # Sparse directional handling marks, not cloudy all-over grunge.
    scuff=Image.new('L',(n,n));draw=ImageDraw.Draw(scuff)
    for _ in range(38):
        x,y=map(int,rng.integers(10,n-80,2));length=int(rng.integers(8,55))
        draw.line((x,y,x+length,y+int(rng.integers(-4,4))),fill=int(rng.integers(25,95)),width=1)
    marks=np.asarray(scuff.filter(ImageFilter.GaussianBlur(.4)))/255.
    colour=np.uint8(np.clip(colour.astype(float)+marks[:,:,None]*38,0,255))
    rough=np.clip(rough-marks*.15,0,1)
    Image.fromarray(colour).save(MD/'panel-color.png')
    Image.fromarray(np.uint8(rough*255)).save(MD/'panel-rough.png')
    dx,dy=np.gradient(grain*.001)
    normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=2)
    normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(MD/'panel-normal.png')
    metal_noise=rng.normal(0,1,(n,n))
    Image.fromarray(np.uint8(np.clip(.43+metal_noise*.014,0,1)*255)).save(MD/'metal-rough.png')
    label=Image.new('RGB',(1024,384),(224,224,207));d=ImageDraw.Draw(label)
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
    bold=lambda size:ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',size)
    d.rounded_rectangle((5,5,1018,378),radius=20,outline=(67,77,78),width=3)
    d.text((42,20),'INSTRUMENT TRANSPORT',(48,63,66),font=bold(50))
    d.line((42,90,982,90),fill=(83,93,90),width=3)
    d.text((42,108),'C14 - 083',(33,45,47),font=bold(105))
    d.text((46,237),'CHECK LATCHES BEFORE MOVING',(66,75,73),font=font(30))
    for x in range(48,651,7):
        width=2+int(rng.integers(0,4));d.rectangle((x,300,x+width,347),fill=(40,52,52))
    d.text((738,305),'LAB  /  14',(61,73,73),font=bold(31))
    label.save(MD/'label-color.png')
    specs={
        'tc_panel':('panel-color.png','panel-normal.png','panel-rough.png',.0),
        'tc_steel':('[0.49 0.53 0.56 1]',None,'metal-rough.png',.86),
        'tc_edge':('[0.39 0.43 0.46 1]',None,'[0.31 0.31 0.31 0]',.84),
        'tc_rubber':('[0.016 0.019 0.020 1]',None,'[0.79 0.79 0.79 0]',0.),
        'tc_dark':('[0.031 0.039 0.040 1]',None,'[0.65 0.65 0.65 0]',0.),
        'tc_label':('label-color.png',None,'[0.64 0.64 0.64 0]',0.)}
    for name,(color,normal,rough,metal) in specs.items():
        path=lambda value: f'{MAT}/{value}' if value and value.endswith('.png') else value
        text='\n'.join(['// Equipment case trial; new private material','"Layer0"','{',
            '    shader "shaders/complex.shader"','    F_SPECULAR "1"',
            f'    TextureColor "{path(color)}"',
            f'    TextureNormal "{path(normal) or "materials/default/default_normal.tga"}"',
            f'    TextureRoughness "{path(rough)}"','    TextureAmbientOcclusion "materials/default/default_ao.tga"',
            f'    g_flMetalness "{metal}"','    g_flRoughnessScaleFactor "1"','    g_flModelTintAmount "1"','}'])+'\n'
        (MD/(name+'.vmat')).write_text(text,encoding='utf-8')


def export(model,name):
    K.write_obj(DEST/(name+'.obj'),model,name)
    K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,model)
    points=np.array([p for polys in model.polygons.values() for points,n in polys for p in points])
    return {'triangles':model.triangle_count() if hasattr(model,'triangle_count') else sum(len(p)-2 for ps in model.polygons.values() for p,n in ps),
        'boundsPlan':[points.min(0).tolist(),points.max(0).tolist()],
        'materials':model.material_overrides}


def main():
    assert not DEST.exists() or not any(DEST.iterdir()), 'Refuse to overwrite a previous candidate'
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    protected=[ROOT/'Assets/models/maps/collider'/f'collider_detail{ext}' for ext in ('.obj','.mtl','.vmdl')]
    protected.append(ROOT/'Assets/scenes/maps/Collider/collider.scene')
    guards={p.relative_to(ROOT).as_posix():sha(p) for p in protected}
    before,provenance=baseline();after=candidate();materials()
    report={'status':'candidate-only-not-used-by-map','editorAvailable':False,'engineCompilation':'pending',
        'baseline':provenance,'models':{'before':export(before,'before'),'after':export(after,'after')},
        'originalAssetsSHA256':guards,'sameAuthoredCollision':True,
        'nativePreview':False,'previewRenderer':'Blender Cycles; matched lighting, camera, scale and exposure'}
    # The source collision is one identical box in both review resources.
    for a,b in zip(before.boxes[0][:3],after.boxes[0][:3]):assert np.allclose(a,b)
    assert before.boxes[0][3]==after.boxes[0][3]=='plastic'
    for path,value in guards.items():assert sha(ROOT/path)==value,path
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    (Path(__file__).parent/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
