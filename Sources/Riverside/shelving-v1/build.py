"""Replace four luminous shelf boxes with stocked, non-emissive retail gondolas for review."""
from pathlib import Path
import sys,json,hashlib,collections,re,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
RES='models/maps/riverside/shelving-v1';MAT='materials/riverside/shelving-v1'
MODEL=REVIEW/'Assets'/RES;MATERIAL=REVIEW/'Assets'/MAT;OUT=REVIEW/'output/riverside/shelving-v1'
for folder in (MODEL,MATERIAL,OUT):folder.mkdir(parents=True,exist_ok=True)
font='C:/Windows/Fonts/arialbd.ttf';regular='C:/Windows/Fonts/arial.ttf'
rng=np.random.default_rng(4761);size=1024
y,x=np.mgrid[0:size,0:size]/(size-1)
coarse=np.asarray(Image.fromarray(rng.integers(0,256,(14,14),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
grain=rng.random((size,size));dirt=y**4*(.2+.8*coarse)
paint=np.zeros((size,size,3))+[152,160,148];paint-=dirt[...,None]*[28,31,29];paint+=(grain[...,None]-.5)*4
Image.fromarray(paint.clip(0,255).astype('uint8')).save(MATERIAL/'paint_color.png')
Image.fromarray(((.52+.23*dirt+.03*grain)*255).clip(0,255).astype('uint8')).save(MATERIAL/'paint_rough.png')
normal=np.zeros((size,size,3),dtype='uint8');normal[:]=[128,128,255];Image.fromarray(normal).save(MATERIAL/'paint_normal.png')
names=['TOMATO\nSOUP','BAKED\nBEANS','SWEET\nCORN','GARDEN\nPEAS'];colours=[(136,46,34),(43,71,99),(171,132,43),(53,92,62)]
for i,(name,base) in enumerate(zip(names,colours)):
    im=Image.new('RGB',(1024,512),base);d=ImageDraw.Draw(im)
    d.rectangle((0,48,1023,78),fill=(204,192,149));d.rectangle((0,420,1023,455),fill=(204,192,149))
    d.multiline_text((512,107),name,anchor='ma',align='center',font=ImageFont.truetype(font,65),fill=(224,219,191),spacing=0)
    d.text((512,351),'NET WT  15 OZ',anchor='mt',font=ImageFont.truetype(regular,24),fill=(218,210,180))
    for yy in range(150,355,17):d.line((47,yy,179,yy),fill=(170,167,147),width=3)
    for xx in range(854,980,6):d.line((xx,285,xx,370),fill=(26,31,27),width=2)
    # Printed illustration, intentionally flat like a paper label, without luminous ink.
    if i==0:
        for cx,cy,r in [(430,294,23),(480,291,26),(537,294,22),(586,294,25)]:
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(183,62,36));d.line((cx-8,cy-r+3,cx+7,cy-r+9),fill=(53,85,43),width=5)
    elif i==2:
        for cx in range(421,600,17):
            for cy in (280,298,316):d.ellipse((cx,cy,cx+11,cy+14),fill=(213,174,60))
    else:
        for cx,cy in [(421,295),(448,280),(477,301),(512,286),(545,308),(578,284)]:d.ellipse((cx-9,cy-7,cx+9,cy+7),fill=(144,110,65) if i==1 else (89,125,62))
    im.save(MATERIAL/f'label{i}_color.png')
for i,(title,base) in enumerate([('ROLLED\nOATS',(153,122,74)),('CRACKERS',(121,71,47))]):
    im=Image.new('RGB',(512,1024),base);d=ImageDraw.Draw(im)
    d.rectangle((15,15,496,1008),outline=(201,190,157),width=4)
    d.multiline_text((256,180),title,anchor='ma',align='center',font=ImageFont.truetype(font,62),fill=(229,222,195))
    d.text((256,420),'PANTRY',anchor='mt',font=ImageFont.truetype(font,36),fill=(216,203,166))
    d.text((256,887),'NET WT  12 OZ',anchor='mt',font=ImageFont.truetype(regular,25),fill=(214,202,165))
    for cy in range(575,790,47):
        for cx in range(110,410,52):d.ellipse((cx,cy,cx+28,cy+15),fill=(188,154,95))
    im.save(MATERIAL/f'box{i}_color.png')
prices=Image.new('RGB',(2048,128),(178,174,147));d=ImageDraw.Draw(prices)
for i,price in enumerate(['1.49','1.99','2.49','1.29','2.99','1.49','2.49','1.99']):
    d.rectangle((i*256+10,7,i*256+236,120),fill=(215,203,143));d.text((i*256+124,57),price,anchor='mm',font=ImageFont.truetype(font,61),fill=(35,39,33))
    d.text((i*256+124,103),'EACH',anchor='mm',font=ImageFont.truetype(regular,19),fill=(51,54,43))
prices.save(MATERIAL/'prices_color.png')
def material(name,color,rough=.6,metal=0):
    color='"'+MAT+'/'+color+'"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    extra=f'TextureNormal "{MAT}/paint_normal.png"\n TextureRoughness "{MAT}/paint_rough.png"' if name=='paint' else f'TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[{rough} {rough} {rough} 0]"'
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
material('paint','paint_color.png');material('steel',(.36,.39,.36),.32,.90);material('rubber',(.025,.031,.025),.88);material('prices','prices_color.png',.75)
material('cardboard',(.32,.235,.13),.85)
for i in range(4):material(f'label{i}',f'label{i}_color.png',.63)
for i in range(2):material(f'box{i}',f'box{i}_color.png',.79)
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def model(lod=0):
    m=K.Model();sides=(12,8,6)[lod]
    def box(c,sz,paint,b=.07):G.bevel_box(m,p(*c),(X,Y,Z),sz,paint,bevel=b if lod<2 else .001)
    def panel(c,right,up,w,h,paint):
        c=np.asarray(c);a=np.asarray(right)*w/2;b=np.asarray(up)*h/2
        m.polygon(paint,[c-a-b,c+a-b,c+a+b,c-a+b],np.cross(a,b),uv=[(0,0),(1,0),(1,1),(0,1)])
    def can(cx,depth,z,variant):
        label=f'label{variant}';start=len(m.polygons[label]);center=p(cx,depth,z)
        profile=[(0,0),(1.18,0),(1.28,.15),(1.28,.28),(1.23,.28),(1.23,4.35),(1.28,4.46),(1.28,4.60),(0,4.60)]
        G.lathe_axis(m,center,Z,profile,['steel','steel','steel','steel',label,'steel','steel','steel'],sides=sides)
        for index in range(start,len(m.polygons[label])):
            points,_=m.polygons[label][index];angles=[(math.atan2(q[0]-center[0],-(q[1]-center[1]))/(2*math.pi)+.5+(.5 if depth<0 else 0))%1 for q in points]
            if max(angles)-min(angles)>.5:angles=[a+1 if a<.5 else a for a in angles]
            m.polygon_uvs[(label,index)]=[(u,(q[2]-z-.28)/4.07) for u,q in zip(angles,points)]
        if lod==0:box((cx,depth,z+4.63),(.42,.70,.055),'steel',.06)
    def carton(cx,depth,z,variant,side):
        label=f'box{variant}';start=len(m.polygons[label]);height=7.65 if variant==0 else 6.8
        G.bevel_box(m,p(cx,depth,z+height/2),(X,Y,Z),(4.8,2.8,height),{'default':'cardboard',('+y' if side>0 else '-y'):label},bevel=.06 if lod<2 else .001)
        for index in range(start,len(m.polygons[label])):
            pts,_=m.polygons[label][index]
            m.polygon_uvs[(label,index)]=[((q[0]-cx)/4.8*side+.5,(q[2]-z)/height) for q in pts]
    # Two-sided steel gondola, solid center sheet, feet, adjustable shelf brackets.
    box((0,0,3.1),(69,35.5,5.4),'paint',.20)
    box((0,0,.55),(66.6,33.6,1.1),'rubber',.12)
    box((0,0,30.3),(66,.40,50.6),'paint',.09)
    for cx in (-33.3,33.3):
        box((cx,0,28),(1.2,2.2,56),'paint',.12)
        if lod<2:
            for zz in range(10,54,4):
                for side in (-1,1):box((cx,side*1.11,zz),(.24,.028,.9),'rubber',.02)
    for level,z in enumerate((5.7,19.7,33.7,47.7)):
        for side in (-1,1):
            box((0,side*9.0,z),(66,16.6,.58),'paint',.09)
            box((0,side*17.44,z-.05),(66,.45,1.18),'paint',.07)
            panel(p(0,side*17.685,z-.05),X*side,Z,65.6,.85,'prices')
            if lod<2:
                for cx in (-31.9,31.9):box((cx,side*8.9,z-.72),(.30,15.7,1.25),'paint',.07)
            for col,cx in enumerate(np.linspace(-28.5,28.5,8)):
                if (level,col,side) in [(1,2,1),(2,5,-1),(3,7,1),(0,6,-1)]:continue
                kind=(col+level)%3
                if kind==0:carton(float(cx),side*12.8,z+.30,(col+level)%2,side)
                else:can(float(cx),side*12.8,z+.30,(col+level)%4)
            if lod<2:
                for col,cx in enumerate((-24.,-8.,8.,24.)):
                    if level==3 and col==2:continue
                    can(cx,side*6.5,z+.30,(col+level+1)%4)
    for paint,polys in m.polygons.items():
        for index,(pts,normal) in enumerate(polys):
            if (paint,index) in m.polygon_uvs:continue
            if abs(normal[2])>.6:uv=[((q[0]+35)/70,(-q[1]+18)/36) for q in pts]
            elif abs(normal[0])>.7:uv=[((-q[1]+18)/36,q[2]/56) for q in pts]
            else:uv=[((q[0]+35)/70,q[2]/56) for q in pts]
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons};m.tile_overrides={paint:48 for paint in m.polygons}
    return m
triangles=[]
for lod in range(3):triangles.append(K.write_obj(MODEL/f'gondola_lod{lod}.obj',model(lod),f'gondola_lod{lod}'))
K.write_vmdl(MODEL/'gondola.vmdl',RES,'gondola_lod0',model())
t=(MODEL/'gondola.vmdl').read_text();start=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=t.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{_class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/gondola_lod{i}.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{exclude_by_default = false exception_list = []}}}},' for i in range(3))
groups='\n'.join(f'{{_class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"]}},' for i,d in enumerate((0,10,25)))
(MODEL/'gondola.vmdl').write_text(t[:start]+f'{{_class = "RenderMeshList" children = [{files}]}},\n{{_class = "LODGroupList" children = [{groups}]}},'+t[end:],encoding='utf-8')
def legacy(m,e,n,z):
    R.box(m,e-18,e+18,n-35,n+35,z,z+56,{'default':'rs_wood'},'wood')
    for zz in (z+18,z+38,z+56):
        P.lit(m,'window',np.array((e-18.3,n,zz-7)),P.right_for((-1,0)),12,off=0,w=68)
        P.lit(m,'window',np.array((e+18.3,n,zz-7)),P.right_for((1,0)),12,off=0,w=68)
local=K.Model();legacy(local,0,0,0);R.configure(local);local=P.place(local,(0,0,0),90);K.write_model(MODEL,RES,'legacy_shelving',local)
absolute=K.Model();positions=[]
for e in (140,270):
    for n in (765,875):legacy(absolute,e,n,20);positions.append([n,-e,20])
R.configure(absolute);K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_shelving')
def records(path):
    lines=path.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';out=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):out.append((i,(paint,tuple(sorted(v[int(p.split('/')[0])-1] for p in l.split()[1:])))))
    return lines,out
_,keys=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(k for _,k in keys)
public=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';current=public.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',current):
    path=ROOT/'Assets'/resource
    if not path.exists():continue
    lines,faces=records(path)
    if not wanted-collections.Counter(k for _,k in faces):source=path;break
assert source,'Original shelving changed: inspect active input'
removed=set()
for i,key in faces:
    if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted and len(removed)==96
(MODEL/'store_without_shelving.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_shelving.mtl'),encoding='utf-8')
(MODEL/'store_without_shelving.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_shelving.vmdl').write_text(current.replace(str(source.relative_to(ROOT/'Assets')).replace('\\','/'),RES+'/store_without_shelving.obj'),encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(preview_only=True,triangles=triangles,removed_original_triangles=96,positions=positions,yaw=90,collision_dimensions=[36,70,56],source_model=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),source_vmdl=str(public.relative_to(ROOT)).replace('\\','/'),source_vmdl_sha256=sha(public),files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for folder in (MODEL,MATERIAL) for p in folder.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
