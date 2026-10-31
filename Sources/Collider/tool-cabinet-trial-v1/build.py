"""Offline whole-object tool-cabinet proposal; never installs or edits a map."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
import psutil
process=psutil.Process();process.nice(psutil.IDLE_PRIORITY_CLASS)
process.cpu_affinity(process.cpu_affinity()[-2:])
from pathlib import Path
from collections import defaultdict
import hashlib,json,math,re,sys
import numpy as np
import scipy.ndimage as ndi
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_operators as O
import collider_detail_geometry as D
import boxyard_map as B
import ares_materials as AM
from belltower_furniture import face
HERE=Path(__file__).parent
OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet'
RESOURCE='models/props/collider/tool-cabinet-trial-v1'
MAT='materials/collider/tool-cabinet-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((-650.,160.,0.));UP=np.array((0.,0.,1.));X=np.array((1.,0.,0.));FRONT=np.array((0.,-1.,0.))
LO=np.array((-44.,-24.,0.));HI=np.array((44.,24.,51.5))
CHARTS=[(0,1,2),(0,1,2),(1,0,2),(1,0,2),(2,0,1),(2,0,1)]
PAINTS={'mc_paint':((47,65,71),.56,0.),'mc_frame':((49,55,57),.62,0.),
        'mc_stainless':((139,143,142),.40,.91),'mc_rubber':((37,39,37),.78,0.),
        'mc_alloy':((121,126,122),.43,.82),'mc_black':((24,28,29),.68,0.)}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
SHAPES=[];WHEELS=[]


def protected():
    paths=list((ROOT/'Assets/models/maps/collider').glob('*'))
    paths+=[ROOT/'Assets/scenes/maps/Collider/collider.scene']
    paths+=list((ROOT/'Tools').glob('collider*.py'))
    for kind in ('models/props','materials'):
        paths += [p for p in (ROOT/'Assets'/kind/'collider').rglob('*')
                  if 'tool-cabinet-trial-v1' not in p.as_posix()]
    return {p.relative_to(ROOT).as_posix():sha(p) for p in paths
            if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png','.scene','.py')}


def baseline():
    model=K.Model();vs=[];uv=[];ns=[];paint='';count=0
    path=ROOT/'Assets/models/maps/collider/collider_detail.obj'
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append((-a,n,z))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append((-a,n,z))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f '):
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            points=[vs[v] for v,t,n in ids]
            if all(-694.01<=p[0]<=-605.99 and 135.99<=p[1]<=184.01 and -.01<=p[2]<=51.51 for p in points):
                points=np.asarray(points)-ORIGIN
                model.polygon(paint,points,uv=[uv[t] for v,t,n in ids],normals=[ns[n] for v,t,n in ids]);count+=1
    assert count==2420,('actual saved-case selection',count)
    M.configure(model)
    # Copy and verify the saved collider, rather than assuming its bounds from the render mesh.
    text=path.with_suffix('.vmdl').read_text();found=[]
    for block in re.findall(r'\{\s*_class = "PhysicsShapeBox"[\s\S]*?\n\s*\}',text):
        values={k:np.fromstring(v,sep=',') for k,v in re.findall(r'(origin|angles|dimensions) = \[([^]]+)\]',block)}
        if np.allclose(values['origin'],K.to_world(ORIGIN+(0,0,26.5)),atol=1e-4):found.append((block,values))
    assert len(found)==1 and np.allclose(found[0][1]['dimensions'],(80,42,47))
    assert np.allclose(found[0][1]['angles'],(0,-90,0))
    model.collision_box((-40,-21,3),(40,21,50),'plastic')
    (OUT/'saved-original-collider.txt').write_text(found[0][0]+'\n')
    return model


def block(m,p,size,paint='mc_paint',r=.4,b=.12,axes=np.eye(3)):
    O.round_block(m,np.array(p,float),size,paint,r,b,axes=axes,segments=5)


def clip_box(m,lo,hi,name,surface='metal'):
    m.collision_box(lo,hi,surface)
    SHAPES.append({'name':name,'kind':'box','lo':list(lo),'hi':list(hi),'surface':surface})


def hull(m,points,name,surface='metal'):
    points=np.asarray(points,float);m.hull(points,surface)
    SHAPES.append({'name':name,'kind':'hull','points':points.tolist(),'surface':surface})


def rounded_hull(m,size,z0,z1,r,name):
    # Same rounded outline as the visible cabinet, with 22.5-degree corner intervals.
    points=[(*p,z) for z in (z0,z1) for p in O.outline(*size,r,segments=4)]
    hull(m,points,name)


def screw(m,p,normal=FRONT,r=.34):
    p=np.array(p,float);normal=np.array(normal,float)
    O.turned(m,p,normal,[(r*1.45,0),(r*1.45,.11)],'mc_alloy',16)
    O.turned(m,p+normal*.11,normal,[(r,0),(r,.35),(r*.82,.43)],'mc_alloy',6)


def label(m,p,w,h,index=0,normal=FRONT):
    p=np.array(p,float);right=X if normal[1]<0 else -X
    points=[p-right*w/2-UP*h/2,p+right*w/2-UP*h/2,p+right*w/2+UP*h/2,p-right*w/2+UP*h/2]
    y0=index/4.;y1=(index+1)/4.
    face(m,'mc_label',points,normal,uv=[(0,1-y1),(1,1-y1),(1,1-y0),(0,1-y0)])


def wheel(m,x,y,yaw):
    c=np.array((x,y,4.2));a=np.array((math.cos(yaw),math.sin(yaw),0.));side=np.cross(UP,a)
    profile=[(3.6,-1.65),(4.13,-1.3),(4.2,-.9),(4.2,.9),(4.13,1.3),(3.6,1.65)]
    O.turned(m,c,a,profile,'mc_rubber',64)
    # Sidewall bead and separate cast hub are grounded on the tyre, not a flat clip box.
    for sign in (-1,1):
        O.turned(m,c,a,[(2.35,sign*1.66),(2.25,sign*1.91)] if sign>0 else [(2.25,-1.91),(2.35,-1.66)],'mc_alloy',40)
        screw(m,c+a*(sign*1.94),a*sign,.48)
        # Pressed fork cheeks and their axle bosses.
        axes=np.array((a,side,UP));p=c+a*sign*2.32+UP*2.6
        block(m,p,(.65,3.9,5.2),'mc_alloy',.31,.16,axes)
        centre=np.array(p);sizes=np.array((.65,3.9,5.2))
        m.oriented_box(centre,axes,sizes,None,'metal')
        SHAPES.append({'name':f'fork {x} {y} {sign}','kind':'oriented-box','centre':centre.tolist(),'axes':axes.tolist(),'size':sizes.tolist(),'surface':'metal'})
    O.turned(m,(x,y,8.8),UP,[(3.35,0),(3.35,.4),(2.7,.8),(2.7,1.9)],'mc_alloy',40)
    block(m,(x,y,10.7),(8.3,7.6,.9),'mc_frame',.65,.15)
    clip_box(m,(x-4.15,y-3.8,10.25),(x+4.15,y+3.8,11.15),'caster mounting plate')
    # Convex support points follow the tyre's actual bevelled profile.
    rim=[]
    for radius,offset in profile:
        for theta in np.linspace(0,math.tau,32,endpoint=False):
            rim.append(c+a*offset+side*math.cos(theta)*radius+UP*math.sin(theta)*radius)
    hull(m,rim,f'tyre {x} {y}','rubber')
    O.tube(m,(x,y,9.5),(x,y,11.4),2.25,'mc_alloy',24)
    # Brake tab on the forward pair.
    if y<0:
        block(m,c+side*4.0+UP*2.1,(3.7,3.2,.4),'mc_frame',.35,.1,axes)
        for off in (-.9,0,.9):O.tube(m,c+side*(3.1+off*.1)+a*off+UP*2.35,c+side*5+a*off+UP*2.35,.12,'mc_rubber',8)
    WHEELS.append({'centre':c.tolist(),'axis':a.tolist(),'profile':profile,'groundZ':0.})


def candidate():
    SHAPES.clear();WHEELS.clear();m=K.Model()
    # Fabricated shell with actual panel thickness and recessed drawer gaps.
    block(m,(0,0,12.0),(76,38,2),'mc_frame',1.2,.3)
    block(m,(-37.3,0,29.6),(1.4,38,35.2),'mc_paint',.45,.15)
    block(m,(37.3,0,29.6),(1.4,38,35.2),'mc_paint',.45,.15)
    block(m,(0,18.4,29.6),(74.6,1.2,35.2),'mc_paint',.45,.15)
    block(m,(0,0,46.8),(76,38,1.6),'mc_frame',.8,.2)
    block(m,(0,-18.25,29),(73.1,1,33.8),'mc_black',.35,.1)
    # Full cabinet volume is a solid cover surface, while the caster clearance stays open.
    rounded_hull(m,(76,38),11,47.6,1.2,'closed cabinet body')
    block(m,(0,0,48.7),(78,40,2.2),'mc_stainless',1.35,.28)
    rounded_hull(m,(78,40),47.6,49.8,1.35,'stainless worktop')
    # Rubber work mat inset into the worktop, thin enough to sit within its rolled edge.
    block(m,(-1,.3,49.86),(70,32,.12),'mc_rubber',.75,.045)
    for y in np.arange(-13,14,1.5):
        O.tube(m,(-34,y,49.94),(32,y,49.94),.055,'mc_black',6)
    # Differently sized drawers have returned lips, recessed runners and hollow metal pulls.
    drawers=[(12.9,20.0),(20.28,26.0),(26.28,31.4),(31.68,36.8),(37.08,41.5),(41.78,46.0)]
    for i,(z0,z1) in enumerate(drawers):
        z=(z0+z1)/2
        block(m,(0,-19.03,z),(72.6,1.45,z1-z0),'mc_paint',.38,.13)
        block(m,(0,-19.81,z1-.6),(69.7,.14,.25),'mc_stainless',.09,.035)
        # Real grip opening behind the bar, with supports at the two ends only.
        block(m,(0,-19.85,z1-1.5),(62,.12,1.7),'mc_black',.28,.04)
        for x in (-30.5,30.5):
            block(m,(x,-20.57,z1-1.45),(1.25,1.55,1.15),'mc_alloy',.27,.10)
            screw(m,(x,-21.39,z1-1.45),FRONT,.25)
            clip_box(m,(x-.63,-21.35,z1-2.03),(x+.63,-19.8,z1-.87),f'drawer {i} pull end')
        O.tube(m,(-30.5,-21.3,z1-1.45),(30.5,-21.3,z1-1.45),.37,'mc_stainless',20)
        clip_box(m,(-30.5,-21.67,z1-1.82),(30.5,-20.93,z1-1.08),f'drawer {i} grip')
        # Individual drawer identifiers make the equipment readable at close range.
        label(m,(-29,-19.8,z0+.75),8.2,.85,1)
    # Recessed key barrel and ID plate set into the top rail.
    O.turned(m,(30,-19.91,46.8),FRONT,[(.74,0),(.74,.22),(.55,.33)],'mc_alloy',32)
    face(m,'mc_black',[(29.94,-20.28,46.465),(30.06,-20.28,46.465),
                       (30.06,-20.28,47.135),(29.94,-20.28,47.135)],FRONT)
    label(m,(-17,-19.02,46.85),29,1.0,0)
    # Folded corner guards, grounded caster plates and physical lower rail scuffs.
    for x in (-36.6,36.6):
        block(m,(x,-19.06,29.6),(2.1,.65,34.1),'mc_frame',.45,.16)
        for z in (14.5,44.5):screw(m,(x,-19.43,z),FRONT,.34)
    for x in (-31.5,31.5):
        for y in (-13.8,13.8):wheel(m,x,y,math.radians(12 if y<0 else 0))
    # End push handle: two brackets and the bar; its open middle has no collision box.
    for y in (-11.,11.):
        block(m,(38.55,y,40),(2.1,1.45,1.5),'mc_alloy',.3,.12)
        clip_box(m,(37.5,y-.725,39.25),(39.6,y+.725,40.75),'push handle bracket')
    O.tube(m,(39.5,-11,40),(39.5,11,40),.55,'mc_rubber',24)
    clip_box(m,(38.95,-11,39.45),(40.05,11,40.55),'push handle grip')
    # Rear service panel, fasteners and formed ventilation recesses.
    block(m,(0,19.12,30),(57,.27,24),'mc_frame',.6,.10)
    for z in (20.5,39.5):
        for x in (-25.5,25.5):screw(m,(x,19.3,z),-FRONT,.32)
    for z in np.arange(23,36,2.4):
        block(m,(0,19.31,z),(38,.10,.63),'mc_black',.22,.025)
        block(m,(0,19.42,z+.32),(38.4,.30,.20),'mc_paint',.08,.035)
    label(m,(0,19.02,16.2),28,3.0,2,-FRONT)
    # Small weld runs remain on the structural joints, not scattered over flat panels.
    for x in (-32.,32.):
        for j in range(10):
            O.turned(m,(x-.9+j*.2,-18.45,12.9),UP,[(.16,0),(.20,.09),(.12,.18)],'mc_alloy',8)
    assign_uvs(m)
    for paint in m.polygons:
        m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=12.
    return m


def assign_uvs(m):
    for paint in PAINTS:
        for i,(points,n) in enumerate(m.polygons[paint]):
            axis=int(np.argmax(abs(n)));chart=axis*2+int(n[axis]<0);_,u,v=CHARTS[chart]
            m.polygon_uvs[(paint,i)]=[((chart%3+.015+.97*(p[u]-LO[u])/(HI[u]-LO[u]))/3,
                                     1-(chart//3+1-(.015+.97*(p[v]-LO[v])/(HI[v]-LO[v])))/2) for p in points]


def materials(m):
    width,height=2046,1364;cw=ch=682
    for paint,(base,rough,met) in PAINTS.items():
        edges=defaultdict(list)
        for i,(pts,n) in enumerate(m.polygons[paint]):
            coords=m.polygon_uvs[(paint,i)]
            for j,a in enumerate(pts):
                k=(j+1)%len(pts);key=tuple(sorted((tuple(np.round(a,4)),tuple(np.round(pts[k],4)))))
                edges[key].append((n,coords[j],coords[k]))
        wear=Image.new('L',(width,height));draw=ImageDraw.Draw(wear)
        for records in edges.values():
            if len(records)==2:
                angle=math.acos(float(np.clip(records[0][0]@records[1][0],-1,1)))
                if angle<math.radians(15):continue
                intensity=int(255*min(1.,angle/(math.pi*.5)))
            elif len(records)==1:intensity=75
            else:continue
            for n,a,b in records:draw.line((a[0]*width,(1-a[1])*height,b[0]*width,(1-b[1])*height),fill=intensity,width=2)
        edge=ndi.gaussian_filter(np.asarray(wear,dtype=np.float32)/255,.65)
        rng=np.random.default_rng(103079+sum(map(ord,paint)))
        noise=rng.standard_normal((height,width));fine=ndi.gaussian_filter(noise,.6);fine/=fine.std()
        mid=ndi.gaussian_filter(noise,5);mid/=mid.std()
        # Controlled coating texture: no broad black patches on the flat drawer faces.
        chips=np.clip(edge*2.0*np.clip(.25+.65*mid+.14*fine,0,1),0,1) if met<.5 else np.zeros_like(edge)
        if paint in ('mc_rubber','mc_black'):chips*=0
        scratches=Image.new('L',(width,height));d=ImageDraw.Draw(scratches)
        for _ in range(400 if met>.5 else 130):
            x,y=rng.uniform(0,width),rng.uniform(0,height)
            d.line((x,y,x+rng.uniform(2,24),y+rng.uniform(-1.3,1.3)),fill=int(rng.uniform(10,65)),width=1)
        sc=np.asarray(scratches,dtype=float)/255
        c=np.array(base)[None,None,:]*(1+.007*fine[...,None]+.006*mid[...,None])
        c=c*(1-chips[...,None])+np.array((109,112,106))*chips[...,None]
        c*=1-sc[...,None]*.16
        rr=np.clip(rough+.016*fine+.018*mid-.17*chips+.12*sc,.25,.93)
        mm=np.clip(met+.86*chips,0,.95)
        bump=fine*(.00020 if met<.5 else .000045)-chips*.0023-sc*.0005
        if paint=='mc_rubber':
            bump+=mid*.00013
        nm=np.full((height,width,3),128,np.uint8)
        for chart,(_,u,v) in enumerate(CHARTS):
            row,col=divmod(chart,3);sl=np.s_[row*ch:(row+1)*ch,col*cw:(col+1)*cw]
            n=AM.normals(bump[sl],(cw/(HI[u]-LO[u]),ch/(HI[v]-LO[v])))
            nm[sl]=np.uint8(np.clip((n*.5+.5)*255,0,255))
        for suffix,array in (('color',np.uint8(np.clip(c,0,255))),('rough',np.uint8(rr*255)),('metal',np.uint8(mm*255)),('normal',nm)):
            Image.fromarray(array).save(MD/(paint+'_'+suffix+'.png'))
        path=f'{MAT}/{paint}'
        text=O.vmat(paint,path+'_color.png',path+'_normal.png',path+'_rough.png')
        text=text.replace('    g_flMetalness "0.0"',f'    F_METALNESS_TEXTURE "1"\n    TextureMetalness "{path}_metal.png"')
        (MD/(paint+'.vmat')).write_text(text)
    labels=Image.new('RGB',(2048,1024),(192,194,179));d=ImageDraw.Draw(labels)
    rows=[('COLLIDER / TECHNICAL SERVICES','MAINTENANCE 07'),('PRECISION TOOLS','RETURN CLEAN AND DRY'),
          ('MOBILE SERVICE CABINET / MC-07','SWL 350 kg  |  APPLY BOTH WHEEL BRAKES'),('INSPECT BEFORE USE','SERIAL MC-0247')]
    for i,(title,subtitle) in enumerate(rows):
        y=i*256;d.rectangle((14,y+12,2034,y+244),outline=(54,65,61),width=5)
        d.text((1024,y+84),title,font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',69),anchor='mm',fill=(37,47,45))
        d.text((1024,y+177),subtitle,font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',46),anchor='mm',fill=(62,72,66))
    labels.save(MD/'labels_color.png');(MD/'mc_label.vmat').write_text(O.vmat('mc_label',f'{MAT}/labels_color.png',rough='[0.65 0.65 0.65 0]'))


def main():
    assert not (HERE/'installed.json').exists(),'Do not rebuild an installed asset'
    if '--geometry-only' in sys.argv:
        report=json.loads((HERE/'candidate.json').read_text())
        for p,h in report['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p
        after=candidate();K.write_model(DEST,RESOURCE,'after',after)
        report['models']['after']={'triangles':after.triangle_count(),'meshSHA256':sha(DEST/'after.obj'),
                                   'boxes':len(after.boxes),'hulls':len(after.hulls)}
        report['collisionShapes']=SHAPES;report['wheels']=WHEELS
        for p in (HERE/'candidate.json',OUT/'manifest.json'):p.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'geometryOnly':True,'after':report['models']['after'],'mapUnchanged':True}))
        return
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);MD.mkdir(parents=True,exist_ok=True)
    guards=protected();print('Protected original sources recorded',flush=True)
    before=baseline();print('Actual saved case and collider extracted',flush=True)
    after=candidate();print('Replacement geometry and compound collision built',flush=True)
    materials(after);print('PBR finishes complete',flush=True)
    for path in before.material_overrides.values():
        material=ROOT/'Assets'/path;guards['Assets/'+path]=sha(material)
        for tex in re.findall(r'Texture\w+\s+"([^"]+)"',material.read_text()):
            p=ROOT/'Assets'/tex
            if not tex.startswith('[') and p.is_file():guards['Assets/'+tex]=sha(p)
    variants={}
    for name,model in (('before',before),('after',after)):
        K.write_model(DEST,RESOURCE,name,model)
        variants[name]={'triangles':model.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj')),
                        'boxes':len(model.boxes),'hulls':len(model.hulls)}
    for p,h in guards.items():assert sha(ROOT/p)==h,p
    report={'status':'candidate-only-not-installed','userApproved':False,'installedInMap':False,
            'originalRetained':True,'editorUsed':False,'engineCompilation':'pending','nativeCollisionAndAppearance':'pending',
            'planOrigin':ORIGIN.tolist(),'baselineSource':'Assets/models/maps/collider/collider_detail.obj',
            'beforeIsActualSavedMesh':True,'models':variants,'protectedSourceSHA256':guards,
            'collisionDesign':'Separate rounded cabinet/worktop hulls, profiled tyre hulls, fork/handle boxes; open underside',
            'collisionShapes':SHAPES,'wheels':WHEELS,
            'newDetails':['folded cabinet panels and separated returned drawer fronts','hollow pulls, rolled stainless worktop and rubber mat',
                          'swivelling caster forks, cast hubs, treaded rubber tyres and brakes','geometry-derived coating loss and physical joints',
                          'rear service panel and individual labels'],
            'workload':{'priority':'idle','cpuAffinity':process.cpu_affinity(),'gpuUsed':False}}
    for p in (HERE/'candidate.json',OUT/'manifest.json'):p.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('protectedSourceSHA256','collisionShapes','wheels')}))


if __name__=='__main__':main()
