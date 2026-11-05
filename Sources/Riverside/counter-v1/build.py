"""Author a review-only replacement for Lucky Stop's plain checkout-counter box."""
from pathlib import Path
import sys,json,hashlib,re,collections,math
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).parent;REVIEW=HERE.parents[2]
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_map as R
RES='models/maps/riverside/counter-v1';MAT='materials/riverside/counter-v1'
MODEL=REVIEW/'Assets'/RES;MATERIAL=REVIEW/'Assets'/MAT;OUT=REVIEW/'output/riverside/counter-v1'
for folder in (MODEL,MATERIAL,OUT):folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(7261);w,h=2048,512
yy,xx=np.mgrid[0:h,0:w]
def noise(n):return np.asarray(Image.fromarray(rng.integers(0,256,(max(2,int(n*h/w)),n),dtype='uint8')).resize((w,h),Image.Resampling.BICUBIC),float)/255
coarse=noise(28);fine=noise(900)
wear=np.exp(-np.minimum(yy,h-1-yy)/22)
colour=np.zeros((h,w,3))+[133,128,106]
colour+=(coarse[...,None]-.5)*9+(fine[...,None]-.5)*5
colour-=wear[...,None]*[10,12,11]
# Small accumulated abrasion and one old cup ring, kept quieter than the surface itself.
marks=Image.new('L',(w,h),0);draw=ImageDraw.Draw(marks)
for _ in range(115):
    x=int(rng.integers(0,w));y=int(rng.integers(0,h));length=int(rng.integers(4,60));draw.line((x,y,x+length,y+int(rng.integers(-5,6))),fill=int(rng.integers(15,58)),width=1)
draw.arc((1430,150,1540,260),5,315,fill=70,width=4)
sm=np.asarray(marks,float)/255
colour-=sm[...,None]*[28,24,17]
Image.fromarray(colour.clip(0,255).astype('uint8')).save(MATERIAL/'laminate_color.png')
rough=np.clip(.40+.13*coarse+.12*wear+.2*sm,0,1)
Image.fromarray((rough*255).astype('uint8')).save(MATERIAL/'laminate_rough.png')
dy,dx=np.gradient((fine-.5)*.05-sm*.08);normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
Image.fromarray(((normal+1)*127.5).clip(0,255).astype('uint8')).save(MATERIAL/'laminate_normal.png')
def material(name,color,rough=.6,metal=0,tint=(1,1,1),normal=None,roughmap=None):
    color='"'+color+'"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    normal='"'+normal+'"' if normal else '"materials/default/default_normal.tga"'
    rough='"'+roughmap+'"' if roughmap else f'"[{rough} {rough} {rough} 0]"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {color}
 TextureNormal {normal}
 TextureRoughness {rough}
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[{' '.join(map(str,tint))} 1]"
}}
''')
material('laminate',MAT+'/laminate_color.png',normal=MAT+'/laminate_normal.png',roughmap=MAT+'/laminate_rough.png')
material('wood','materials/gunsmith_range/bench_oak_color.png',tint=(.70,.60,.47),normal='materials/gunsmith_range/bench_oak_normal.png',roughmap='materials/gunsmith_range/bench_oak_roughness.png')
material('trim',(.035,.043,.038),.48)
material('recess',(.018,.022,.018),.86)
material('steel',(.30,.32,.30),.32,.92)
material('core',(.18,.12,.068),.82)
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(20,12,8)[lod]
    def box(c,sz,paint,b=.08):G.bevel_box(m,p(*c),(X,Y,Z),sz,paint,bevel=b if lod<2 else min(b,.025))
    def cyl(c,axis,length,r,paint):G.lathe_axis(m,p(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
    # Original outer footprint and 40-inch top: the installed register stays seated at exactly the same height.
    box((0,-.7,2.3),(106,24.2,4.6),'trim',.15)
    box((0,-.4,20.5),(106,26.2,33.6),'wood',.16)
    box((0,0,38.8),(110,30,2.0),'trim',.22)
    box((0,0,39.76),(109.5,29.5,.48),{'default':'trim','+z':'laminate'},.12)
    # Front recessed oak panels, rails and stiles. Their physical offsets catch the existing store lighting.
    for x in (-34.,0.,34.):
        box((x,12.82,21.4),(31.3,.12,25.3),'recess',.08)
        box((x,12.96,21.4),(30.4,.18,24.4),'wood',.12)
    for x in (-52.,-17.,17.,52.):box((x,13.28,21.0),(1.5,1.15,31.9),'wood',.11)
    for z in (5.6,36.2):box((0,13.18,z),(105.4,.95,1.7),'wood',.10)
    # The operator side has four separate storage doors, narrow reveal lines, hinges and pulls.
    for x in (-39.,-13.,13.,39.):
        box((x,-13.66,20.8),(25.5,.18,30.4),'recess',.07)
        box((x,-13.83,20.8),(24.6,.40,29.5),'wood',.14)
        if lod<2:
            for z in (29.,32.5):cyl((x+7.6,-14.06,z),-Y,.57,.18,'steel')
            G.tube(m,[p(x+7.6,-14.63,29),p(x+7.6,-14.63,32.5)],.18,'steel',sides=sides)
            for z in (11.,30.):
                box((x-11.9,-14.08,z),(.76,.13,1.82),'steel',.06)
                cyl((x-12.15,-14.15,z-.7),Z,1.4,.14,'steel')
        else:box((x+7.6,-14.25,30.75),(.25,.28,3.7),'steel',.04)
    # End panel reveals and a lower skirt: no paper-thin open bottom.
    for x in (-53.07,53.07):
        box((x,-.4,21.0),(.14,22.6,28.0),'recess',.10)
        box((x+(-.10 if x<0 else .10),-.4,21.0),(.16,21.9,27.3),'wood',.10)
    # Tubular steel foot rail sits inside the old collision footprint.
    if lod<2:
        path=[p(-49,12.0,8)]
        path += [p(-46.6-2.4*math.cos(t),12.0+2.4*math.sin(t),8) for t in np.linspace(0,math.pi/2,5)[1:]]
        path += [p(46.6,14.4,8)]
        path += [p(46.6+2.4*math.sin(t),12.0+2.4*math.cos(t),8) for t in np.linspace(0,math.pi/2,5)[1:]]
        G.tube(m,path,.52,'steel',sides=sides)
    else:G.tube(m,[p(-48,14.4,8),p(48,14.4,8)],.52,'steel',sides=sides)
    for x in (-37.,0.,37.):
        cyl((x,12.85,8),Y,.24,1.02,'steel')
        cyl((x,12.99,8),Y,1.0,.29,'steel')
        if lod==0:
            for z in (7.36,8.64):cyl((x,13.12,z),Y,.055,.105,'trim')
    if lod==0:
        # Small edge losses expose the chipboard core without covering every edge in rust.
        for x,length,z in [(-41.,1.8,39.03),(19.,1.15,39.34),(44.,.65,38.7)]:
            box((x,15.005,z),(length,.03,.10),'core',.015)
    for paint,polys in m.polygons.items():
        for index,(points,normal) in enumerate(polys):
            uv=[]
            for q in points:
                x,d,z=q[0],-q[1],q[2]
                if paint=='laminate':u=(x+55)/110;v=(d+15)/30
                elif abs(normal[2])>.6:u=x/30;v=d/24
                elif abs(normal[0])>.7:u=d/24;v=z/36
                else:u=x/30;v=z/36
                uv.append((float(u),float(v)))
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons}
    m.tile_overrides={paint:36 for paint in m.polygons}
    return m
counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'counter_lod{lod}.obj',model(lod),f'counter_lod{lod}'))
K.write_vmdl(MODEL/'counter.vmdl',RES,'counter_lod0',model())
text=(MODEL/'counter.vmdl').read_text();start=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=text.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/counter_lod{i}.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {t} meshes = ["lod{i}"] }},' for i,t in enumerate((0,15,35)))
(MODEL/'counter.vmdl').write_text(text[:start]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+text[end:])
old=K.Model();R.box(old,-55,55,-15,15,0,40,{'default':'rs_wood','+z':'rs_concrete'},'wood');R.configure(old);K.write_model(MODEL,RES,'legacy_counter',old)
absolute=K.Model();R.box(absolute,80,190,920,950,20,60,{'default':'rs_wood','+z':'rs_concrete'},'wood');R.configure(absolute);K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_counter')
def records(path):
    lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';result=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,result
_,oldfaces=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(k for _,k in oldfaces)
public=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';current=public.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',current):
    candidate=ROOT/'Assets'/resource
    if not candidate.exists():continue
    lines,faces=records(candidate);available=collections.Counter(k for _,k in faces)
    if not (wanted-available):source=candidate;break
assert source,'Original counter changed: inspect before replacing'
removed=set()
for i,key in faces:
    if wanted[key]:removed.add(i);wanted[key]-=1
assert len(removed)==12 and not +wanted
(MODEL/'store_without_counter.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_counter.mtl'))
(MODEL/'store_without_counter.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_counter.vmdl').write_text(current.replace(str(source.relative_to(ROOT/'Assets')).replace('\\','/'),RES+'/store_without_counter.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
external=['Assets/materials/gunsmith_range/bench_oak_'+suffix for suffix in ('color.png','normal.png','roughness.png')]
manifest=dict(preview_only=True,triangles=counts,removed_original_triangles=12,position=[935,-135,20],collision_dimensions=[110,30,40],source_model=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),source_vmdl=str(public.relative_to(ROOT)).replace('\\','/'),source_vmdl_sha256=sha(public),external_files={p:sha(ROOT/p) for p in external},files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for folder in (MODEL,MATERIAL) for p in folder.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','external_files')},indent=2))
