"""Author a review-only replacement for Riverside's Lucky Stop ice merchandiser.

python build.py --project-root C:/sbox-projects/hc1/forked-shooter-main
Generated resources stay in this branch until imported through the running editor.
"""
from pathlib import Path
import argparse,sys,json,hashlib,collections,math,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--project-root',type=Path,default=REVIEW)
PROJECT=parser.parse_args().project_root.resolve()
sys.path.insert(0,str(PROJECT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_map as R
import riverside_parts as P

RES='models/maps/riverside/ice-cabinet-v1'
MAT='materials/riverside/ice-cabinet-v1'
OUT=REVIEW/'output/riverside/ice-cabinet-v1'
MODEL=REVIEW/'Assets'/RES
MATERIAL=REVIEW/'Assets'/MAT
for folder in (OUT,MODEL,MATERIAL):folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(98137)
size=1024
yy,xx=np.mgrid[0:size,0:size]/(size-1)
def noise(grid):
    a=Image.fromarray(rng.integers(0,256,(grid,grid),dtype=np.uint8))
    return np.asarray(a.resize((size,size),Image.Resampling.BICUBIC),float)/255
coarse=noise(11);fine=noise(160);grain=noise(420)
dirt=yy**5*(.25+.75*coarse)
edge=np.exp(-np.minimum(xx,1-xx)*75)
chips=(rng.random((size,size))<(.003+.065*edge+.012*yy**8))&(fine>.47)
colour=np.zeros((size,size,3))+[205,211,201]
colour-=dirt[...,None]*np.array([42,46,43])
colour+=(coarse[...,None]-.5)*7+(grain[...,None]-.5)*4
colour[chips]=[111,80,52]
rough=np.clip(.55+.24*dirt+.10*(fine-.5)+chips*.15,0,1)
height=.12*(grain-.5)+.15*(fine-.5)-chips*.08
dy,dx=np.gradient(height)
n=np.stack([-dx*2,-dy*2,np.ones_like(dx)],axis=-1);n/=np.linalg.norm(n,axis=2,keepdims=True)
Image.fromarray(colour.clip(0,255).astype('uint8')).save(MATERIAL/'enamel_color.png')
Image.fromarray((rough*255).astype('uint8')).save(MATERIAL/'enamel_rough.png')
Image.fromarray(((n+1)*127.5).clip(0,255).astype('uint8')).save(MATERIAL/'enamel_normal.png')

# The door is a real panel; only its printed markings use this small texture.
door=Image.fromarray(colour.clip(0,255).astype('uint8'))
ink=Image.new('L',(size,size),0);draw=ImageDraw.Draw(ink)
font_path='C:/Windows/Fonts/arialbd.ttf'
font=ImageFont.truetype(font_path,360)
draw.text((size/2,240),'ICE',font=font,anchor='mt',fill=255,stroke_width=1)
small=ImageFont.truetype(font_path,43)
draw.text((size/2,690),'KEEP FROZEN',font=small,anchor='mt',fill=235)
ink_a=np.asarray(ink,float)/255
ink_a*=np.clip(.90+.14*(coarse-.5)-chips*.9,0,1)
arr=np.asarray(door,float)
red=np.zeros_like(arr)+[159,38,31]
arr=arr*(1-ink_a[...,None])+red*ink_a[...,None]
Image.fromarray(arr.clip(0,255).astype('uint8')).save(MATERIAL/'door_color.png')
label=Image.new('RGB',(1024,256),(40,64,68));d=ImageDraw.Draw(label)
d.rectangle((12,12,1011,243),outline=(157,174,167),width=3)
d.text((512,44),'BAGGED ICE',font=ImageFont.truetype(font_path,120),anchor='mt',fill=(221,220,196))
label.save(MATERIAL/'header_color.png')

def material(name,color,roughness=.6,metal=0,normal=None,roughmap=None):
    colour=f'"{MAT}/{color}"' if isinstance(color,str) else '"['+' '.join(map(str,color))+' 0]"'
    normal=f'"{MAT}/{normal}"' if normal else '"materials/default/default_normal.tga"'
    rough=f'"{MAT}/{roughmap}"' if roughmap else f'"[{roughness} {roughness} {roughness} 0]"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {colour}
 TextureNormal {normal}
 TextureRoughness {rough}
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[1 1 1 1]"
}}
''')
material('enamel','enamel_color.png',normal='enamel_normal.png',roughmap='enamel_rough.png')
material('door','door_color.png',normal='enamel_normal.png',roughmap='enamel_rough.png')
material('header','header_color.png',.68)
material('rubber',(.025,.032,.029),.88)
material('steel',(.36,.40,.41),.31,.94)
material('recess',(.016,.020,.018),.8)
material('rust',(.15,.075,.034),.86,.18)

X=np.array((1.,0.,0.));Y=np.array((0.,-1.,0.));Z=np.array((0.,0.,1.))
def point(x,d,z):return X*x+Y*d+Z*z
def make(lod):
    m=K.Model();sides=(20,12,8)[lod]
    def box(c,sz,paint,bevel=.12,paints=None):
        G.bevel_box(m,point(*c),(X,Y,Z),sz,paints or paint,bevel=bevel)
    def cyl(c,axis,length,r,paint):
        G.lathe_axis(m,point(*c),axis,[(0.,0.),(r,0.),(r,length),(0.,length)],paint,sides=sides)
    def screw(x,d,z):
        cyl((x,d,z),Y,.07,.14,'steel')
        if lod==0:
            box((x,d+.078,z),(.20,.012,.038),'recess',.005)
            box((x,d+.078,z),(.038,.012,.20),'recess',.005)
    # Same 38 x 30 x 60 inch cabinet volume as the original; corner chamfers catch porch lighting.
    box((0,-.45,30.2),(38,29.1,59.6),'enamel',.48)
    box((0,0,2.0),(37.6,29.4,2.7),'rubber',.35)
    for x in (-15.2,15.2):
        for d in (-11.4,11.4):cyl((x,d,0),Z,.85,1.22,'rubber')
    # An inset gasket remains visible around the solid insulated door.
    box((0,14.13,33.8),(33.5,.30,42.8),'rubber',.40)
    box((0,14.49,33.8),(31.8,.78,41.2),'enamel',.46,
        paints={'default':'enamel','+y':'door'})
    # Raised header and recessed intake, with actual spaced louvres rather than a flat vent picture.
    box((0,14.18,57.35),(33.4,.50,3.65),'enamel',.24,
        paints={'default':'enamel','+y':'header'})
    box((0,14.13,7.6),(32.4,.18,8.4),'recess',.15)
    count=(10,8,5)[lod]
    for z in np.linspace(4.0,11.1,count):box((0,14.58,float(z)),(30.8,.68,.26 if lod<2 else .36),'enamel',.07)
    for x in (-16.2,16.2):box((x,14.54,7.6),(.48,.75,8.4),'enamel',.12)
    for z in (3.35,11.85):box((0,14.52,z),(32.8,.65,.5),'enamel',.13)
    # Stainless pull handle with two standoffs; the grip is separate from the door surface.
    for z in (29.,39.):
        cyl((-11.8,14.9,z),Y,.25,.65,'rubber')
        cyl((-11.8,15.04,z),Y,1.48,.32,'steel')
    G.tube(m,[point(-11.8,16.52,29),point(-11.8,16.52,39)],.32,'steel',sides=sides)
    # Three hinge barrels, mounting leaves and a keyed latch.
    for z in (17.,34.,50.):
        box((15.68,15.01,z),(1.18,.18,2.65),'steel',.09)
        cyl((16.22,15.05,z-1.18),Z,2.36,.29,'steel')
        if lod<2:
            for zz in (z-.85,z+.85):screw(15.45,15.14,zz)
    cyl((-9.5,14.94,34),Y,.18,.43,'steel')
    box((-9.5,15.14,34),(.055,.015,.43),'recess',.01)
    if lod<2:
        for x in (-15.,15.):
            for z in (3.4,11.85,57.35):screw(x,14.95,z)
        # Side service cover and folded flange, with thin seams and fasteners.
        box((19.01,-2.5,15),(.14,17.,18.),'rubber',.11)
        box((19.10,-2.5,15),(.14,16.55,17.55),'enamel',.08)
        for d in (-9.7,4.7):
            for z in (7.4,22.6):cyl((19.2,d,z),X,.07,.13,'steel')
    if lod==0:
        # A few isolated chips at exposed corners, not uniformly orange edges.
        for x,d,z in [(18.85,13.8,6.8),(-18.85,13.8,8.0),(16.7,14.83,2.8),(-14.3,14.86,3.45)]:
            box((x,d,z),(.28,.035,.10),'rust',.01)
    # Explicit panel UVs keep dirt near the floor and the lettering upright.
    for paint,polys in m.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            coords=[]
            for p in pts:
                x,d,z=p[0],-p[1],p[2]
                if paint=='door':u=(x+15.44)/30.88;v=(z-13.66)/40.28
                elif paint=='header':u=(x+16.46)/32.92;v=(z-55.77)/3.16
                elif abs(normal[2])>.7:u=(x+19)/38;v=(d+15)/30
                elif abs(normal[0])>.7:u=(d+15)/30;v=z/60
                else:u=(x+19)/38;v=z/60
                coords.append((float(u),float(v)))
            m.polygon_uvs[(paint,index)]=coords
    m.material_overrides={p:f'{MAT}/{p}.vmat' for p in m.polygons}
    m.tile_overrides={p:60 for p in m.polygons}
    m.oriented_box(np.array((0.,0.,30.)),(X,np.array((0.,1.,0.)),Z),(38,30,60),{'default':None},'metal')
    return m

triangles=[]
models=[]
for lod in range(3):
    m=make(lod);models.append(m)
    triangles.append(K.write_obj(MODEL/f'ice_cabinet_lod{lod}.obj',m,f'ice_cabinet_lod{lod}'))
K.write_vmdl(MODEL/'ice_cabinet.vmdl',RES,'ice_cabinet',models[0])
text=(MODEL/'ice_cabinet.vmdl').read_text()
start=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"')
end=text.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/ice_cabinet_lod{i}.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {t} meshes = ["lod{i}"] }},' for i,t in enumerate((0,20,45)))
text=text[:start]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+text[end:]
(MODEL/'ice_cabinet.vmdl').write_text(text)

# Recreate only the original ice box for the control image, then remove exactly its faces from a review copy.
old=K.Model()
R.obox(old,np.array((0.,0.,30.)),(1,0,0),(38,30,60),'rs_fridge','metal')
P.lit(old,'vending',np.array((0.,-15.2,30.)),P.right_for((0,-1)),52,off=0,w=36)
R.configure(old)
K.write_model(MODEL,RES,'legacy_ice',old)
absolute=K.Model()
offset=np.array((160.,622.,20.))
for paint,polys in old.polygons.items():
    for pts,normal in polys:absolute.polygon(paint,[p+offset for p in pts],normal)
R.configure(absolute)
K.write_obj(OUT/'legacy-ice-absolute.obj',absolute,'legacy_ice_absolute')
def records(path):
    lines=path.read_text().splitlines(keepends=True)
    vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
    paint='';result=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,result
_,faces=records(OUT/'legacy-ice-absolute.obj')
wanted=collections.Counter(k for _,k in faces)
source_vmdl=PROJECT/'Assets/models/maps/riverside/riverside_store.vmdl'
source_text=source_vmdl.read_text()
# The store may already combine reviewed upgrades. Find the active input that actually contains the old ice box.
source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',source_text):
    candidate=PROJECT/'Assets'/resource
    if not candidate.exists():continue
    candidate_lines,candidate_records=records(candidate)
    available=collections.Counter(key for _,key in candidate_records)
    if not (wanted-available):
        source=candidate;lines=candidate_lines;current=candidate_records;break
assert source is not None,'No active store mesh contains the original ice box; inspect current ModelDoc inputs.'
removed=set()
for i,key in current:
    if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted,'Original ice geometry changed; inspect the source before replacing anything.'
(MODEL/'store_without_ice.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_ice.mtl'))
(MODEL/'store_without_ice.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_ice.vmdl').write_text(source_text.replace(str(source.relative_to(PROJECT/'Assets')).replace('\\','/'),RES+'/store_without_ice.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for folder in (MODEL,MATERIAL) for p in folder.iterdir() if p.is_file()}
manifest=dict(preview_only=True,triangles=triangles,removed_original_triangles=len(removed),position=[622,-160,20],
    source_model=str(source.relative_to(PROJECT)).replace('\\','/'),source_sha256=sha(source),
    source_vmdl=str(source_vmdl.relative_to(PROJECT)).replace('\\','/'),source_vmdl_sha256=sha(source_vmdl),files=files)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
