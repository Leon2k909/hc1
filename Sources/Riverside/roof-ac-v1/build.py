"""Build a review-only rooftop air conditioner; never regenerate or write the saved map."""
from pathlib import Path
import sys,json,hashlib,collections,re,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/roof-ac-v1'
STAGE=OUT/'stage'
RES='models/props/riverside/roof_ac_v1'
MAT='materials/riverside/roof_ac_v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
for d in (OUT,MODEL,MATERIAL):d.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(75319)
size=1024;yy,xx=np.mgrid[0:size,0:size]/(size-1)
def noise(n):
    return np.asarray(Image.fromarray(rng.integers(0,256,(n,n),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
cloud=noise(13);grain=noise(420);stain=noise(55)
runoff=np.exp(-np.minimum(xx,1-xx)*28)*(.35+.65*stain)
soil=(1-yy)**6*(.35+.65*cloud)
color=np.zeros((size,size,3))+[187,181,154]
color+=(cloud[...,None]-.5)*12+(grain[...,None]-.5)*4
color-=soil[...,None]*[47,44,30]+runoff[...,None]*[14,17,13]
Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/'shroud_color.png')
rough=np.clip(.65+.18*soil+.09*cloud+.035*grain,0,1)
Image.fromarray((rough*255).astype('uint8')).save(MATERIAL/'shroud_rough.png')
dy,dx=np.gradient((grain-.5)*.16+(stain-.5)*.09)
n=np.stack((-dx*1.5,-dy*1.5,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=2,keepdims=True)
Image.fromarray(((n+1)*127.5).clip(0,255).astype('uint8')).save(MATERIAL/'shroud_normal.png')
label=Image.new('RGB',(768,256),(167,155,108));draw=ImageDraw.Draw(label)
draw.rectangle((10,10,757,245),outline=(54,59,51),width=4)
for y,text,font_size in [(22,'AIR CONDITIONER',55),(103,'115 V  /  60 Hz',40),(177,'DISCONNECT POWER BEFORE SERVICE',25)]:
    draw.text((384,y),text,anchor='mt',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',font_size),fill=(49,54,46))
label.save(MATERIAL/'service_color.png')
def material(name,color,rough=.6,metal=0):
    c=f'"{MAT}/{color}"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    extra=f'TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[{rough} {rough} {rough} 0]"'
    if name=='shroud':extra=f'TextureNormal "{MAT}/shroud_normal.png"\n TextureRoughness "{MAT}/shroud_rough.png"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {c}
 {extra}
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
}}
''')
material('shroud','shroud_color.png')
material('base',(.11,.125,.115),.68,.72)
material('dark',(.012,.017,.015),.9)
material('steel',(.24,.27,.25),.45,.88)
material('fan',(.075,.085,.073),.61,.65)
material('service','service_color.png',.78)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.))
def make(lod):
    m=K.Model();segments=(40,24,16)[lod]
    def box(c,s,paint='shroud',b=0):
        if b and lod<2:G.bevel_box(m,np.asarray(c),(X,Y,Z),s,paint,bevel=b)
        else:m.oriented_box(np.asarray(c),(X,Y,Z),s,paint)
    def rod(a,b,r,paint='steel',sides=6):G.tube(m,[np.asarray(a),np.asarray(b)],r,paint,sides=sides)
    def cyl(c,r,h,paint='steel',sides=None):
        G.lathe_axis(m,np.asarray(c),Z,[(0,0),(r,0),(r,h),(0,h)],paint,sides=sides or (16,10,6)[lod])
    # Compression gasket and folded base pan stay in the old 34 x 30 footprint.
    box((0,0,.22),(33.9,29.8,.44),'dark',.1)
    # A flexible curb closes the old unit's air gap above the office's shallow 1:12 gable roof.
    for ya,yb in ((-14.9,0),(0,14.9)):
        za=-.5-abs(ya)/12;zb=-.5-abs(yb)/12
        for side in (-1,1):
            pts=[(side*16.95,ya,za),(side*16.95,yb,zb),(side*16.95,yb,.05),(side*16.95,ya,.05)]
            m.polygon('dark',pts if side==1 else list(reversed(pts)))
        m.polygon('dark',[(-16.95,ya,za),(-16.95,yb,zb),(16.95,yb,zb),(16.95,ya,za)])
    for side in (-1,1):
        y=side*14.9;z=-.5-14.9/12
        pts=[(-16.95,y,z),(16.95,y,z),(16.95,y,.05),(-16.95,y,.05)]
        m.polygon('dark',pts if side==-1 else list(reversed(pts)))
    box((0,0,1.0),(33.5,29.4,1.1),'base',.22)
    # The shroud is hollow: its top is replaced below by an annular panel surrounding a real fan well.
    G.bevel_box(m,np.array((0.,0.,7.)),(X,Y,Z),(34,30,11),'shroud',bevel=1.2,skip=('+z',))
    # Opening the top also omits these two end bevels in the shared box helper; close them explicitly.
    for side in (-1,1):
        points=[np.array((side*15.8,-13.8,12.5)),np.array((side*17.,-13.8,11.3)),
                np.array((side*17.,13.8,11.3)),np.array((side*15.8,13.8,12.5))]
        m.polygon('shroud',points if side==1 else list(reversed(points)),np.array((side,0,1)))
    fc=np.array((4.,0.,0.));r=8.3
    angles=list(np.linspace(0,2*math.pi,segments,endpoint=False))
    angles += [math.atan2(y,x-fc[0])%(2*math.pi) for x in (-15.8,15.8) for y in (-13.8,13.8)]
    angles=sorted(set(angles));outer=[];inner=[]
    for a in angles:
        d=np.array((math.cos(a),math.sin(a),0.))
        t=min((15.8-fc[0])/d[0] if d[0]>1e-6 else (-15.8-fc[0])/d[0] if d[0]<-1e-6 else 1e9,
              13.8/abs(d[1]) if abs(d[1])>1e-6 else 1e9)
        outer.append(fc+d*t+Z*12.5);inner.append(fc+d*r+Z*12.5)
    for i in range(len(angles)):
        j=(i+1)%len(angles)
        m.polygon('shroud',[inner[i],outer[i],outer[j],inner[j]],Z)
        m.polygon('dark',[inner[i],inner[j],inner[j]-Z*3,inner[i]-Z*3])
    cyl(fc+Z*9.45,8.29,.10,'dark',segments)
    # Motor, stationary twisted sheet-metal blades and guard are physically separated by depth.
    cyl(fc+Z*9.6,1.5,1.65,'fan')
    cyl(fc+Z*11.25,1.7,.33,'steel')
    blades=4
    for k in range(blades):
        rings=[]
        for f in np.linspace(0,1,(8,5,3)[lod]):
            radius=1.55+f*5.95;a=k*math.pi/2-.25+f*.36
            rings.append([fc+np.array((radius*math.cos(a+t),radius*math.sin(a+t),10.5+f*.45+t*.5)) for t in (-.31,.31)])
        for i in range(len(rings)-1):
            m.polygon('fan',[rings[i][0],rings[i+1][0],rings[i+1][1],rings[i][1]],both_sides=True)
    for radius in ((2.6,4.3,6.1,8.1) if lod==0 else (4.3,8.1) if lod==1 else (8.1,)):
        G.torus(m,fc+Z*12.76,Z,radius,.075,'steel',seg=segments,sides=5 if lod==0 else 4)
    for a in np.linspace(0,2*math.pi,(8,6,4)[lod],endpoint=False):
        end=fc+np.array((8.13*math.cos(a),8.13*math.sin(a),12.76))
        rod(fc+Z*12.76,end,.085,sides=5 if lod==0 else 4)
    cyl(fc+Z*12.65,.65,.22,'steel')
    # Intake louvres project from dark recesses down both sides.
    for side in (-1,1):
        box((side*17.012,0,6.8),(.025,22.5,5.6),'dark')
        for z in np.linspace(4.35,9.25,(7,5,3)[lod]):
            box((side*17.11,0,float(z)),(.20,21.5,.22),'shroud')
        for y in (-11.25,11.25):box((side*17.10,y,6.8),(.22,.32,5.8),'shroud')
    # Exposed coil face at the front, with protection bars over the fins.
    box((0,-15.012,6.7),(26,.025,6.0),'dark')
    for x in np.linspace(-12.4,12.4,(40,24,12)[lod]):box((float(x),-15.055,6.7),(.075,.065,5.5),'steel')
    for z in (4.0,6.7,9.4):box((0,-15.17,z),(26.4,.18,.18),'base')
    # Removable service cover, fasteners and faded technical label on the opposite end.
    box((0,15.012,6.5),(26,.025,5.8),'dark')
    box((0,15.08,6.5),(25.5,.12,5.3),'shroud',.08)
    G.quad(m,'service',np.array((-3.,15.15,6.6)),-X,Z,7.5,2.5,uv=[(0,0),(1,0),(1,1),(0,1)])
    if lod<2:
        for x in (-14.4,14.4):
            for y in (-12.5,12.5):
                cyl((x,y,12.5),.28,.12,'steel',6)
                if lod==0:
                    box((x,y,12.63),(.30,.045,.018),'dark')
                    box((x,y,12.63),(.045,.30,.018),'dark')
        for x in (-11.7,11.7):
            for z in (4.45,8.55):
                G.lathe_axis(m,np.array((x,15.16,z)),Y,[(0,0),(.13,0),(.13,.04),(0,.04)],'steel',sides=8)
        for y in (-10,10):
            box((-14.7,y,1.7),(2.6,1.3,.5),'base',.06)
            cyl((-14.7,y,1.95),.23,.14,'steel',6)
    for paint,polys in m.polygons.items():
        for i,(pts,normal) in enumerate(polys):
            if (paint,i) in m.polygon_uvs:continue
            if abs(normal[2])>.65:uv=[((p[0]+17)/34,(p[1]+15)/30) for p in pts]
            elif abs(normal[0])>.65:uv=[((p[1]+15)/30,p[2]/13.5) for p in pts]
            else:uv=[((p[0]+17)/34,p[2]/13.5) for p in pts]
            m.polygon_uvs[(paint,i)]=uv
    m.material_overrides={p:f'{MAT}/{p}.vmat' for p in m.polygons}
    m.tile_overrides={p:34 for p in m.polygons}
    return m
counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'roof_ac_lod{lod}.obj',make(lod),f'roof_ac_lod{lod}'))
K.write_vmdl(MODEL/'roof_ac.vmdl',RES,'roof_ac_lod0',make(0))
text=(MODEL/'roof_ac.vmdl').read_text();start=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=text.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/roof_ac_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,12,35)))
(MODEL/'roof_ac.vmdl').write_text(text[:start]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+text[end:])

# Recreate only this office unit, matching the original generator's exact geometry.
hits=[];original=P.obox
def record(m,c,d,size,paint,*a,**kw):
    if tuple(size)==(34,30,13):hits.append(np.asarray(c).copy())
    return original(m,c,d,size,paint,*a,**kw)
P.obox=record
try:P.trailer(480,120,'rs_siding_white',seed=51,door_side=1,lit_share=.8,boarded_share=0,door_lit=True)
finally:P.obox=original
assert len(hits)==1
center=hits[0];foot=center-Z*6.5
old=K.Model();P.obox(old,Z*6.5,(1,0,0),(34,30,13),'rs_alu');P.obox(old,Z*13.2,(1,0,0),(26,22,.6),'rs_dark');R.configure(old)
K.write_model(MODEL,RES,'legacy_ac',old)
origin=np.array((-640.,-640.,96.))+foot
absolute=P.place(old,origin,0);R.configure(absolute);K.write_obj(OUT/'legacy_absolute.obj',absolute,'old_ac')
def records(path):
    lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';result=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,result
_,oldfaces=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in oldfaces)
source_vmdl=ROOT/'Assets/models/maps/riverside/riverside_pad.vmdl';source_text=source_vmdl.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',source_text):
    candidate=ROOT/'Assets'/resource
    if not candidate.exists():continue
    lines,current=records(candidate);available=collections.Counter(k for _,k in current)
    if not wanted-available:source=candidate;break
assert source,'Office AC no longer matches the saved mesh; inspect before preparing a review.'
cut=set()
for i,key in current:
    if wanted[key]:cut.add(i);wanted[key]-=1
assert len(cut)==24 and not +wanted
(MODEL/'pad_without_ac.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib pad_without_ac.mtl'))
(MODEL/'pad_without_ac.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'pad_without_ac.vmdl').write_text(source_text.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/pad_without_ac.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,source_vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
manifest=dict(preview_only=True,triangles=counts,removed_old_triangles=len(cut),position=K.to_world(origin).tolist(),
    resource=RES+'/roof_ac.vmdl',background=RES+'/pad_without_ac.vmdl',
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},
    files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
