"""Review-only formed Lucky Stop lightbox and proper gooseneck lamps."""
from pathlib import Path
import sys,json,hashlib,re,collections,math
import numpy as np
from PIL import Image
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_map as R
import riverside_parts as P
import riverside_materials as RM
RES='models/maps/riverside/shop-sign-v1';MAT='materials/riverside/shop-sign-v1'
MODEL=REVIEW/'Assets'/RES;MATERIAL=REVIEW/'Assets'/MAT;OUT=REVIEW/'output/riverside/shop-sign-v1'
for folder in (MODEL,MATERIAL,OUT):folder.mkdir(parents=True,exist_ok=True)
# Extract the original print and illumination mask, retaining the existing sign design.
for name,source in [('face_color.png','rs_lit_color.png'),('face_illum.png','rs_lit_illum.png')]:
    image=Image.open(ROOT/'Assets/materials/riverside'/source);sx,sy,sw,sh=RM.LIT['lucky_stop'];scale=image.width/RM.LIT_ATLAS[0]
    image.crop(tuple(round(v*scale) for v in (sx,sy,sx+sw,sy+sh))).resize((2048,512),Image.Resampling.LANCZOS).save(MATERIAL/name)
rng=np.random.default_rng(542);size=1024;yy,xx=np.mgrid[0:size,0:size]/(size-1)
noise=np.asarray(Image.fromarray(rng.integers(0,256,(16,16),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
grain=rng.random((size,size));dirt=yy**5*(.2+.8*noise)
edge=np.exp(-np.minimum(xx,1-xx)*60)
chips=(rng.random((size,size))<(.012*edge+.001))&(noise>.43)
color=np.zeros((size,size,3))+[172,181,165];color-=dirt[...,None]*[33,36,34];color+=(noise[...,None]-.5)*7+(grain[...,None]-.5)*3;color[chips]=[89,78,58]
Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/'paint_color.png')
Image.fromarray(((.49+.25*dirt+.04*grain)*255).clip(0,255).astype('uint8')).save(MATERIAL/'paint_rough.png')
normal=np.zeros((size,size,3),dtype='uint8');normal[:]=[128,128,255];Image.fromarray(normal).save(MATERIAL/'paint_normal.png')
def material(name,color,rough=.6,metal=0,face=False):
    color='"'+MAT+'/'+color+'"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    extra=f'TextureNormal "{MAT}/paint_normal.png"\n TextureRoughness "{MAT}/paint_rough.png"' if name=='paint' else f'TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[{rough} {rough} {rough} 0]"'
    if face:extra+=f'\n F_SELF_ILLUM 1\n TextureSelfIllumMask "{MAT}/face_illum.png"\n g_flSelfIllumBrightness "0.65"\n g_flSelfIllumAlbedoFactor "1.0"\n g_vSelfIllumTint "[1 1 1 0]"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {color}
 {extra}
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
}}
''',encoding='utf-8')
material('paint','paint_color.png');material('face','face_color.png',.72);material('steel',(.31,.35,.34),.35,.92)
(MATERIAL/'face_toned.vmat').write_bytes((MATERIAL/'face.vmat').read_bytes())
material('rubber',(.02,.027,.022),.86);material('inside',(.56,.60,.52),.46);material('rust',(.18,.092,.042),.86)
bulb=(ROOT/'Assets/materials/riverside/rs_lamp_warm.vmat').read_text(encoding='utf-8')
bulb,n=re.subn(r'(g_flSelfIllumBrightness\s*)"[^"]+"',r'\g<1>"1.0"',bulb);assert n==1
(MATERIAL/'bulb.vmat').write_text(bulb,encoding='utf-8')
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(20,12,8)[lod]
    def box(c,sz,paint,b=.10):G.bevel_box(m,p(*c),(X,Y,Z),sz,paint,bevel=b if lod<2 else min(b,.035))
    def cyl(c,axis,length,r,paint,segments=None):G.lathe_axis(m,p(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=segments or sides)
    def bolt(c,axis=Z,r=.30):
        cyl(c,axis,.07,r*1.55,'steel');cyl(tuple(np.asarray(c)+np.array((0,0,.075))),axis,.22,r,'steel',6)
    def bar(a,b,width,paint):
        a=p(*a);b=p(*b);axis=b-a;length=np.linalg.norm(axis);axis/=length
        other=np.cross(axis,X if abs(np.dot(axis,X))<.9 else Y);other/=np.linalg.norm(other);third=np.cross(axis,other)
        G.bevel_box(m,(a+b)/2,(axis,other,third),(length,width,width),paint,bevel=.10 if lod<2 else .035)
    # Cabinet volume and main image match the original 168 x 8 x 48 inch sign.
    box((0,0,50),(168,8,48),'paint',.65)
    box((0,4.05,50),(162,.15,42),'rubber',.22)
    box((0,4.15,50),(160,.18,40),{'default':'inside','+y':'face'},.075)
    for z in (28.6,71.4):box((0,4.30,z),(164,.80,1.20),'paint',.15)
    for x in (-81.6,81.6):box((x,4.30,50),(1.2,.80,42.8),'paint',.15)
    # Folded rear service cover, hinge leaves, electrical junction and conduit.
    box((0,-4.09,50),(164,.18,44),'paint',.20)
    box((48,-4.25,50),(23,.16,31),'rubber',.15)
    box((48,-4.40,50),(22.4,.18,30.4),'paint',.12)
    if lod<2:
        for z in (41.,59.):
            box((59.5,-4.59,z),(1.1,.18,2.2),'steel',.08);cyl((60,-4.63,z-.9),Z,1.8,.18,'steel')
    box((-59,-5.8,44),(11,3.0,10),'paint',.22)
    box((-59,-7.36,44),(9.8,.14,8.8),'paint',.12)
    if lod<2:G.tube(m,[p(-64,-2,1.5),p(-64,-2,31),p(-59,-5.9,35),p(-59,-5.9,39)],.34,'steel',sides=sides)
    # Two square posts and rear diagonal braces retain the original roof contact points.
    for x in (-64.,64.):
        box((x,0,15),(2.2,2.2,30),'paint',.14)
        box((x,0,.55),(8,8,1.1),'steel',.14)
        bar((x,0,26),(x,-36,4),1.8,'paint')
        box((x,-36,3.65),(7,7,.70),'steel',.12)
        if lod<2:
            for dx in (-2.6,2.6):
                for d in (-2.6,2.6):bolt((x+dx,d,1.12),r=.28);bolt((x+dx,-36+d,4.02),r=.28)
    # Curved gooseneck arms and open reflector shades replace the old lamp boxes.
    for x in (-56.,0.,56.):
        box((x,0,74.3),(5.5,4,.6),'steel',.12)
        path=[p(x,0,74.5),p(x,0,79),p(x,1.2,82),p(x,4.3,84),p(x,8.0,84.4),p(x,11.3,83),p(x,13.6,80.1),p(x,14,79.6)]
        if lod==2:path=path[::2]+[path[-1]]
        G.tube(m,path,.44,'paint',sides=sides)
        profile=[(0,0),(.75,0),(1.0,.5),(1.45,1.1),(3.6,3.0),(3.9,3.25),(3.9,3.50),(3.60,3.50),(3.55,3.20),(1.10,.80),(0,.80)]
        G.lathe_axis(m,p(x,14,79.7),-Z,profile,['paint']*5+['steel']*2+['inside']*3,sides=sides)
        G.lathe_axis(m,p(x,14,76.55),-Z,[(0,0),(.58,0),(.73,.40),(.60,.77),(0,.92)],'bulb',sides=sides)
    if lod<2:
        for z in (28.6,71.4):
            for x in (-78.,-52.,-26.,0.,26.,52.,78.):
                cyl((x,4.72,z),Y,.07,.16,'steel')
                if lod==0:box((x,4.80,z),(.17,.018,.025),'rubber',.003)
        for x in (-72.,0.,72.):cyl((x,3.9,26.75),Y,.12,.29,'rubber')
    if lod==0:
        for x,z,w in [(-67.,28.8,.42),(36.,71.25,.67),(80.9,53.,.22)]:box((x,4.72,z),(w,.018,.10),'rust',.009)
    for paint,polys in m.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            uv=[]
            for q in pts:
                x,d,z=q[0],-q[1],q[2]
                if paint=='face':u=(x+79.925)/159.85;v=(z-30.075)/39.85
                elif abs(normal[2])>.7:u=(x+84)/168;v=(d+40)/58
                elif abs(normal[0])>.7:u=(d+40)/58;v=z/85
                else:u=(x+84)/168;v=(z-26)/48
                uv.append((float(u),float(v)))
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons};m.material_overrides['face']=MAT+'/face_toned.vmat';m.tile_overrides={paint:64 for paint in m.polygons}
    return m
triangles=[]
for lod in range(3):triangles.append(K.write_obj(MODEL/f'shop_sign_lod{lod}.obj',model(lod),f'shop_sign_lod{lod}'))
K.write_vmdl(MODEL/'shop_sign.vmdl',RES,'shop_sign_lod0',model())
t=(MODEL/'shop_sign.vmdl').read_text();start=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=t.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{_class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/shop_sign_lod{i}.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{exclude_by_default = false exception_list = []}}}},' for i in range(3))
groups='\n'.join(f'{{_class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"]}},' for i,d in enumerate((0,20,45)))
(MODEL/'shop_sign.vmdl').write_text(t[:start]+f'{{_class = "RenderMeshList" children = [{files}]}},\n{{_class = "LODGroupList" children = [{groups}]}},'+t[end:],encoding='utf-8')
def legacy(m,offset):
    v=R.v;UP=R.UP;sc=np.asarray(offset,float)+v(0,0,50);r=P.right_for((0,-1));sw=160.;sh=40.;eave=offset[2]
    R.obox(m,sc,(1,0,0),(168,8,48),'rs_dark','metal');P.lit(m,'lucky_stop',sc+v(0,-4,0),r,40,off=.4,w=160);P.sign(m,'sign_back',sc+v(0,4,0),-r,40,off=.4,w=160)
    for k in range(3):
        lp=sc+v(-sw*.35+k*sw*.35,-14,sh/2+6)
        R.obox(m,lp,(1,0,0),(8,6,3),'rs_dark');R.card(m,'rs_lamp_warm',[lp+v(-3.5,-2.5,-1.6),lp+v(3.5,-2.5,-1.6),lp+v(3.5,2.5,-1.6),lp+v(-3.5,2.5,-1.6)],-UP);R.rod(m,lp+v(0,3,0),lp+v(0,12,-2),.6,'rs_steel',5)
    for sx in (-1,1):
        foot=v(sc[0]+sx*64,offset[1],eave);m.beam(foot,foot+UP*30,(2,2),'rs_steel');m.beam(foot+UP*26,v(foot[0],offset[1]+36,eave+4),(1.5,1.5),'rs_steel')
    R.configure(m)
old=K.Model();legacy(old,(0,0,0));K.write_model(MODEL,RES,'legacy_shop_sign',old)
absolute=K.Model();legacy(absolute,(220,514,150));K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_shop_sign')
def records(path):
    lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';out=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):out.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,out
_,keys=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(k for _,k in keys);old_count=sum(wanted.values())
public=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';current=public.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',current):
    path=ROOT/'Assets'/resource
    if not path.exists():continue
    lines,faces=records(path)
    if not wanted-collections.Counter(k for _,k in faces):source=path;break
assert source,'Original roof sign changed: inspect the active source'
removed=set()
for i,key in faces:
    if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted and len(removed)==old_count
(MODEL/'store_without_shop_sign.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_shop_sign.mtl'),encoding='utf-8')
(MODEL/'store_without_shop_sign.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_shop_sign.vmdl').write_text(current.replace(str(source.relative_to(ROOT/'Assets')).replace('\\','/'),RES+'/store_without_shop_sign.obj'),encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
external=['Assets/materials/riverside/'+n for n in ('rs_lit_color.png','rs_lit_illum.png','rs_lit.vmat','rs_lamp_warm.vmat')]
manifest=dict(preview_only=True,triangles=triangles,removed_original_triangles=old_count,position=[514,-220,150],original_cabinet_dimensions=[168,8,48],source_model=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),source_vmdl=str(public.relative_to(ROOT)).replace('\\','/'),source_vmdl_sha256=sha(public),external_files={p:sha(ROOT/p) for p in external},files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for folder in (MODEL,MATERIAL) for p in folder.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','external_files')},indent=2))
