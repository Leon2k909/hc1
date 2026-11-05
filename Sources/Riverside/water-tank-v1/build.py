"""Review-only rebuilt water-tower vessel; existing support frame and lights stay."""
from pathlib import Path
import sys,json,hashlib,collections,re,math,io
import numpy as np
from PIL import Image,ImageFilter
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/water-tank-v1';STAGE=OUT/'stage'
RES='models/props/riverside/water_tank_v1';MAT='materials/riverside/water_tank_v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
for p in (OUT,MODEL,MATERIAL):p.mkdir(parents=True,exist_ok=True)
if '--debug-stack' in sys.argv:
    import faulthandler,ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001|0x0002|0x8000)
    trace=(OUT/'build-stack.log').open('w')
    faulthandler.enable(trace);faulthandler.dump_traceback_later(20,repeat=True,file=trace)
rng=np.random.default_rng(16883600);size=1024;yy,xx=np.mgrid[0:size,0:size]/(size-1)
def png(array,name):
    buffer=io.BytesIO();Image.fromarray(array).save(buffer,format='PNG')
    (MATERIAL/name).write_bytes(buffer.getvalue())
def noise(w,h=None):return np.asarray(Image.fromarray(rng.integers(0,256,(h or w,w),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
cloud=noise(60,12);fine=noise(900,180);rain=noise(180,8)
streak=np.clip((rain-.49)*3,0,1)*(.2+.8*yy)
bottom=yy**7*(.3+.7*cloud);rust=(fine>.71)&(cloud>.57)&((yy>.84)|(rain>.68))
color=np.zeros((size,size,3))+[131,147,154]
color+=(cloud[...,None]-.5)*12+(fine[...,None]-.5)*4
color-=streak[...,None]*[28,30,29]+bottom[...,None]*[28,32,30]
color[rust]=np.stack((102+fine[rust]*12,73+fine[rust]*7,49+fine[rust]*5),axis=-1)
png(color.clip(0,255).astype('uint8'),'shell_color.png')
png(((.57+.16*streak+.12*bottom+.07*fine)*255).clip(0,255).astype('uint8'),'shell_rough.png')
height=cloud*.07+fine*.014+rust*.025;dy,dx=np.gradient(height)
normal=np.dstack((-dx,-dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[...,None]
png(((normal*.5+.5)*255).clip(0,255).astype('uint8'),'shell_normal.png')
# Radial runoff on the conical roof, with subdued patina rather than tiled rust patches.
radius=np.sqrt((xx-.5)**2+(yy-.5)**2);angle=np.arctan2(yy-.5,xx-.5)
roof_cloud=noise(30);roof_fine=noise(360)
run=(np.sin(angle*83+roof_cloud*.8)*.5+.5)*np.clip(radius*1.8,0,1)
roof=np.zeros((size,size,3))+[121,138,144];roof+=(roof_cloud[...,None]-.5)*12
roof-=run[...,None]*[12,14,13]
png(roof.clip(0,255).astype('uint8'),'roof_color.png')
png(((.63+.13*run+.05*roof_fine)*255).clip(0,255).astype('uint8'),'roof_rough.png')
def material(name,color,rough,metal=0):
    c=f'"{MAT}/{color}"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    n=f'{MAT}/shell_normal.png' if name in ('shell','roof') else 'materials/default/default_normal.tga'
    r=f'"{MAT}/{name}_rough.png"' if name in ('shell','roof') else f'"[{rough} {rough} {rough} 0]"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {c}
 TextureNormal "{n}"
 TextureRoughness {r}
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[1 1 1 1]"
}}
''')
material('shell','shell_color.png',.65,.26)
material('roof','roof_color.png',.7,.35)
material('trim',(.22,.28,.29),.57,.45)
material('hardware',(.31,.34,.33),.45,.78)
material('gasket',(.021,.027,.025),.88)
if '--materials-only' in sys.argv:
    m=json.loads((OUT/'manifest.json').read_text())
    m['files']={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2));print('Material staging complete',flush=True);sys.exit()
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.))
unit=lambda p:np.asarray(p,float)/np.linalg.norm(p)
f=unit((*R.WATER_TOWER[1],0));right=P.right_for(f)
letter=K.Model();P.paint(letter,'sticks',f*210.6+Z*115,right,184,tone='white',off=0)
def make(lod):
    m=K.Model();sides=(72,44,28)[lod]
    def axis(c,profile,paint='hardware',along=Z,n=None):G.lathe_axis(m,np.asarray(c),along,profile,paint,sides=n or (14,10,6)[lod])
    def bar(a,b,r,paint='trim'):
        a=np.asarray(a);b=np.asarray(b);length=float(np.linalg.norm(b-a))
        axis(a,[(0,0),(r,0),(r,length),(0,length)],paint,(b-a)/length)
    def tube(pts,r,paint='trim',bend=2):G.tube(m,[np.asarray(p,float) for p in pts],r,paint,sides=(8,6,4)[lod],bend_radius=bend)
    # Dished lower head, rolled knuckle and cylindrical welded courses.
    profile=[(18,-35),(60,-33),(115,-28),(160,-20),(192,-10),(206,-2),(210,6),(210,230)]
    rings=[];normals=[]
    for j,(radius,z) in enumerate(profile):
        a=np.array(profile[max(0,j-1)]);b=np.array(profile[min(len(profile)-1,j+1)]);dr,dz=b-a
        dirs=[np.array((math.cos(t),math.sin(t),0)) for t in np.linspace(0,2*math.pi,sides,endpoint=False)]
        rings.append([d*radius+Z*z for d in dirs]);normals.append([unit(d*dz-Z*dr) for d in dirs])
    for j in range(len(rings)-1):
        for k in range(sides):
            k1=(k+1)%sides;pts=[rings[j][k],rings[j][k1],rings[j+1][k1],rings[j+1][k]]
            ns=[normals[j][k],normals[j][k1],normals[j+1][k1],normals[j+1][k]]
            uv=[(k/sides,(profile[j][1]+35)/265),((k+1)/sides,(profile[j][1]+35)/265),((k+1)/sides,(profile[j+1][1]+35)/265),(k/sides,(profile[j+1][1]+35)/265)]
            G.card(m,'shell',pts,sum(ns),uv=uv,normals=ns)
    before=len(m.polygons['roof'])
    G.lathe(m,np.zeros(3),[(212,230),(209,232),(210*.55,300),(18,340),(0,342)],'roof',sides)
    for i in range(before,len(m.polygons['roof'])):
        pts,_=m.polygons['roof'][i];m.polygon_uvs[('roof',i)]=[(p[0]/430+.5,p[1]/430+.5) for p in pts]
    for z in (6,82,158,229):G.torus(m,Z*z,Z,210.1,.72,'trim',seg=sides,sides=(4,4,3)[lod])
    G.torus(m,Z*230,Z,211.7,1.4,'trim',seg=sides,sides=(6,4,3)[lod])
    # Raised standing seams on the roof, following its original silhouette.
    for t in np.linspace(0,2*math.pi,(24,16,10)[lod],endpoint=False):
        d=np.array((math.cos(t),math.sin(t),0))
        tube([d*210+Z*233,d*(210*.55)+Z*301,d*18+Z*341],.65,'trim',1)
    # Build access hardware separately so it can be rotated onto the visible west flank.
    body=m;m=K.Model()
    # Ladder and safety cage sit beside the park-facing lettering, inside the retained catwalk rail.
    for sy in (-1,1):
        tube([(222,sy*10,9),(222,sy*10,270),(214,sy*10,282),(202,sy*10,269)],1.05)
        for z in (30,100,170,228):
            bar((209.9,sy*10,z),(222,sy*10,z),.7)
            if lod<2:axis((222.1,sy*10,z),[(0,0),(.47,0),(.47,.5),(0,.5)],'hardware',X,n=6)
    for z in np.arange(12,241,12):bar((222,-10,float(z)),(222,10,float(z)),.72,'hardware')
    if lod<2:
        for z in (55,105,155,205,245):
            G.torus(m,np.array((222.,0,z)),Z,18,.65,'trim',seg=(18,12)[lod],sides=4,a0=-math.pi/2,a1=math.pi/2,basis=(X,Y))
            for sy in (-1,1):bar((222,sy*10,z),(222,sy*18,z),.65)
        for t in (-math.pi/4,0,math.pi/4):
            d=np.array((math.cos(t),math.sin(t),0));bar(np.array((222.,0,55))+d*18,np.array((222.,0,245))+d*18,.65)
    # Roof access neck, gasketed lid, hinge, fasteners and grab handle lie on the upper cone's slope.
    n=unit((40/97.5,0,1));u=unit(np.cross(Y,n));c=np.array((90.,0,310.4))
    axis(c,[(16.5,0),(16.5,6.2),(18,6.2),(18,7.3)],'trim',n,n=(28,18,12)[lod])
    axis(c+n*7.3,[(0,0),(18.1,0),(18.1,.6),(0,.6)],'gasket',n,n=(28,18,12)[lod])
    axis(c+n*7.9,[(0,0),(18.4,0),(18.4,1.5),(17.8,2.1),(0,2.1)],'roof',n,n=(32,20,12)[lod])
    for t in np.linspace(0,2*math.pi,(12,8,4)[lod],endpoint=False):
        p=c+n*9.9+u*(16*math.cos(t))+Y*(16*math.sin(t));axis(p,[(0,0),(.52,0),(.52,.55),(0,.55)],'hardware',n,n=6)
    bar(c-u*16-Y*7+n*8,c-u*16+Y*7+n*8,1.0,'hardware')
    tube([c+u*3-Y*4+n*10,c+u*3-Y*4+n*14,c+u*3+Y*4+n*14,c+u*3+Y*4+n*10],.7,'hardware')
    # A downturned vent has an open rolled mouth and a recessed screen.
    pts=[np.array(p,float) for p in [(-75,-30,314),(-75,-30,340),(-93,-30,340),(-93,-30,328)]]
    G.tube(m,pts,3.0,'trim',sides=(16,10,6)[lod],bend_radius=7,caps=False)
    G.torus(m,np.array((-93.,-30,328)),Z,3,.32,'hardware',seg=(16,10,6)[lod],sides=4)
    axis((-93,-30,329),[(0,0),(2.7,0),(2.7,.1),(0,.1)],'gasket')
    body.extend(P.place(m,(0,0,0),180));m=body
    # Original atlas lettering now follows the tank wall instead of floating on a flat card.
    for paint,polys in letter.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            uv=letter.polygon_uvs[(paint,index)];coords=[(float(np.dot(p,right)),float(p[2]),t) for p,t in zip(pts,uv)]
            xmin=min(x for x,z,t in coords);xmax=max(x for x,z,t in coords);zmin=min(z for x,z,t in coords);zmax=max(z for x,z,t in coords)
            def tex(x,z):
                # The atlas quad's actual corner order is kept through the cylindrical projection.
                near=sorted(coords,key=lambda a:abs(a[0]-x)+abs(a[1]-z))[0];return np.array(near[2])
            uv00,uv10,uv11,uv01=tex(xmin,zmin),tex(xmax,zmin),tex(xmax,zmax),tex(xmin,zmax)
            for k in range((32,20,12)[lod]):
                count=(32,20,12)[lod];s0=k/count;s1=(k+1)/count
                pair=[];norm=[];uvs=[]
                for s,t in ((s0,0),(s1,0),(s1,1),(s0,1)):
                    x=xmin+(xmax-xmin)*s;z=zmin+(zmax-zmin)*t;d=f*math.cos(x/210.7)+right*math.sin(x/210.7)
                    pair.append(d*210.7+Z*z);norm.append(d)
                    uvs.append(((1-s)*(1-t)*uv00+s*(1-t)*uv10+s*t*uv11+(1-s)*t*uv01).tolist())
                G.card(m,paint,pair,sum(norm),uv=uvs,normals=norm)
    for paint in m.polygons:
        m.material_overrides[paint]=f'materials/riverside/{paint}.vmat' if paint.startswith('rs_') else f'{MAT}/{paint}.vmat'
        m.tile_overrides[paint]=96
    return m
print('Textures ready',flush=True);counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'tank_lod{lod}.obj',make(lod),f'tank_lod{lod}'));print('LOD',lod,counts[-1],flush=True)
K.write_vmdl(MODEL/'tank.vmdl',RES,'tank_lod0',make(0))
text=(MODEL/'tank.vmdl').read_text();a=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=text.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/tank_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,30,80)))
(MODEL/'tank.vmdl').write_text(text[:a]+f'{{ _class = "RenderMeshList" children = [{files}] }},\n{{ _class = "LODGroupList" children = [{groups}] }},'+text[b:])
if '--geometry-only' in sys.argv:
    m=json.loads((OUT/'manifest.json').read_text());m['triangles']=counts
    m['files']={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()}
    (OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({'triangles':counts,'geometry_updated':True}));sys.exit()
old=K.Model();P.cylinder(old,(0,0),210,0,230,'rs_tank',28,bottom='rs_tank')
G.lathe(old,np.zeros(3),[(212,230),(210*.55,300),(18,340),(0,342)],'rs_tank',28)
P.paint(old,'sticks',f*210.6+Z*115,right,184,tone='white',off=0)
R.configure(old);K.write_model(MODEL,RES,'legacy_tank',old)
origin=np.array(R.WATER_TOWER[0],float)+Z*1100
absolute=P.place(old,origin,0);R.configure(absolute);K.write_obj(OUT/'legacy_absolute.obj',absolute,'old_tank')
def records(p):
    lines=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];mat='';r=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):mat=l.split()[1]
        if l.startswith('f '):r.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,r
_,oldfaces=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in oldfaces)
vmdl=ROOT/'Assets/models/maps/riverside/riverside_backdrop.vmdl';vt=vmdl.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
    p=ROOT/'Assets'/resource
    if not p.exists():continue
    lines,faces=records(p)
    if not wanted-collections.Counter(k for i,k in faces):source=p;break
assert source,'Original water-tank faces no longer match the public backdrop mesh.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==len(oldfaces)==224 and not +wanted
# Extract the saved faces/UVs/normals for the legacy image instead of substituting a fresh export.
absolute_text=''.join(l for i,l in enumerate(lines) if not l.startswith('f ') or i in cut)
(OUT/'legacy_absolute.obj').write_text(absolute_text)
obj_origin=np.array((-origin[0],origin[2],origin[1]));local=[]
for line in absolute_text.splitlines(keepends=True):
    if line.startswith('v '):line='v '+' '.join(f'{v:.6f}' for v in np.array(list(map(float,line.split()[1:4])))-obj_origin)+'\n'
    if line.startswith('mtllib '):line='mtllib legacy_tank.mtl\n'
    local.append(line)
(MODEL/'legacy_tank.obj').write_text(''.join(local));(MODEL/'legacy_tank.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'backdrop_without_tank.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib backdrop_without_tank.mtl'))
(MODEL/'backdrop_without_tank.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'backdrop_without_tank.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/backdrop_without_tank.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),plan_position=origin.tolist(),removed_old_triangles=len(cut),resource=RES+'/tank.vmdl',background=RES+'/backdrop_without_tank.vmdl',
       protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
