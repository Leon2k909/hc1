"""Review-only Lucky Stop register: replace the original plain 16x12x12 box."""
from pathlib import Path
import sys,json,hashlib,re,collections,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).parent
REVIEW=HERE.parents[2]
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_map as R
RES='models/maps/riverside/register-v1'
MAT='materials/riverside/register-v1'
MODEL=REVIEW/'Assets'/RES;MATERIAL=REVIEW/'Assets'/MAT
OUT=REVIEW/'output/riverside/register-v1'
for p in (MODEL,MATERIAL,OUT):p.mkdir(parents=True,exist_ok=True)
font='C:/Windows/Fonts/arial.ttf';bold='C:/Windows/Fonts/arialbd.ttf'
rng=np.random.default_rng(718)
size=1024;yy,xx=np.mgrid[0:size,0:size]/(size-1)
def noise(n):return np.asarray(Image.fromarray(rng.integers(0,256,(n,n),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
n=noise(12);f=noise(300)
edge=np.exp(-np.minimum(xx,1-xx)*65)
dirt=yy**4*(.3+n*.7)
colour=np.zeros((size,size,3))+[165,166,143]
colour-=dirt[...,None]*[22,23,22];colour+=(n[...,None]-.5)*10+(f[...,None]-.5)*5
scrapes=(rng.random((size,size))<(.012*edge+.001))&(f>.5)
colour[scrapes]=[74,78,71]
Image.fromarray(colour.clip(0,255).astype('uint8')).save(MATERIAL/'housing_color.png')
Image.fromarray(((.49+.22*dirt+.06*f)*255).clip(0,255).astype('uint8')).save(MATERIAL/'housing_rough.png')
dy,dx=np.gradient((f-.5)*.09)
normal=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
Image.fromarray(((normal+1)*127.5).clip(0,255).astype('uint8')).save(MATERIAL/'housing_normal.png')
keys=[('7','ivory'),('8','ivory'),('9','ivory'),('DEPT 1','teal'),('DEPT 2','teal'),('FEED','grey'),
      ('4','ivory'),('5','ivory'),('6','ivory'),('DEPT 3','teal'),('DEPT 4','teal'),('VOID','red'),
      ('1','ivory'),('2','ivory'),('3','ivory'),('SUB','grey'),('TOTAL','amber'),('CLEAR','grey'),
      ('0','ivory'),('00','ivory'),('.','ivory'),('CASH','amber'),('CARD','teal'),('NO SALE','grey')]
atlas=Image.new('RGB',(1024,1024),(40,43,39));d=ImageDraw.Draw(atlas)
colours={'ivory':(190,186,158),'teal':(57,88,79),'grey':(88,94,87),'red':(114,52,43),'amber':(145,110,49)}
for i,(label,color) in enumerate(keys):
    x=i%8*128;y=i//8*128
    d.rectangle((x,y,x+127,y+127),fill=colours[color])
    ink=(30,33,28) if color=='ivory' else (217,216,186)
    d.text((x+64,y+64),label,anchor='mm',font=ImageFont.truetype(bold,48 if len(label)<3 else 19),fill=ink)
atlas.save(MATERIAL/'keys_color.png')
display=Image.new('RGB',(1024,256),(4,16,12));d=ImageDraw.Draw(display)
d.text((53,18),'TOTAL',font=ImageFont.truetype(font,34),fill=(37,85,65))
d.text((961,212),'12.50',anchor='rs',font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',158),fill=(71,166,116))
display.save(MATERIAL/'display_color.png')
receipt=Image.new('RGB',(512,1024),(200,195,172));d=ImageDraw.Draw(receipt)
for y,text in [(60,'LUCKY STOP'),(160,'BAGGED ICE  3.00'),(230,'DRINKS      8.50'),(300,'TAX         1.00'),(430,'TOTAL      12.50'),(600,'CASH       15.00'),(670,'CHANGE      2.50'),(840,'THANK YOU')]:
    d.text((256,y),text,anchor='mt',font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',32),fill=(59,63,54))
receipt.save(MATERIAL/'receipt_color.png')
badge=Image.new('RGB',(512,128),(40,47,42));d=ImageDraw.Draw(badge)
d.text((256,61),'LUCKY STOP',anchor='mm',font=ImageFont.truetype(bold,56),fill=(176,174,149));badge.save(MATERIAL/'badge_color.png')
def material(name,color,rough=.6,metal=0,emission=0):
    color='"'+MAT+'/'+color+'"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    extra=''
    if name=='housing':extra=f'TextureNormal "{MAT}/housing_normal.png"\n TextureRoughness "{MAT}/housing_rough.png"'
    else:extra=f'TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[{rough} {rough} {rough} 0]"'
    if emission:extra+=f'\n F_SELF_ILLUM 1\n TextureSelfIllumMask "[1 1 1 0]"\n g_flSelfIllumBrightness "{emission}"\n g_vSelfIllumTint "[1 1 1 1]"'
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
''')
material('housing','housing_color.png')
material('keys','keys_color.png',.5)
material('display','display_color.png',.24,0,.32)
material('receipt','receipt_color.png',.87)
material('badge','badge_color.png',.55)
material('black',(.027,.034,.029),.7)
material('drawer',(.067,.081,.073),.43,.55)
material('steel',(.34,.36,.34),.31,.9)
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
angle=math.atan(.38);B=Y*math.cos(angle)-Z*math.sin(angle);N=Y*math.sin(angle)+Z*math.cos(angle)
def model(lod=0):
    m=K.Model();sides=(16,10,8)[lod]
    def box(c,sz,paint,b=.09,axes=(X,Y,Z)):G.bevel_box(m,p(*c),axes,sz,paint,bevel=b if lod<2 else .001)
    def cyl(c,axis,length,r,paint):G.lathe_axis(m,p(*c),axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
    def panel(c,right,up,w,h,paint):
        c=np.asarray(c);right=np.asarray(right)*w/2;up=np.asarray(up)*h/2
        m.polygon(paint,[c-right-up,c+right-up,c+right+up,c-right+up],np.cross(right,up),uv=[(0,0),(1,0),(1,1),(0,1)])
    # Heavy cash drawer, separate seam and folded metal front.
    box((0,0,1.9),(16,12,3),'black',.18)
    box((0,6.035,1.95),(15.35,.16,2.28),'drawer',.11)
    box((0,6.145,2.28),(10.1,.08,.31),'black',.035)
    box((0,6.26,2.12),(9.4,.20,.18),'steel',.035)
    cyl((5.9,6.15,1.67),Y,.10,.28,'steel')
    box((5.9,6.265,1.67),(.046,.012,.24),'black',.006)
    for x in (-6.6,6.6):
        for depth in (-4.6,4.6):cyl((x,depth,0),Z,.46,.47,'black')
    # Sloped electronic-register housing. Plane rises toward the printer and display at the back.
    pts=[p(-7.5,5.4,3.45),p(7.5,5.4,3.45),p(7.5,-5.4,3.45),p(-7.5,-5.4,3.45),
         p(-7.5,5.4,4.3),p(7.5,5.4,4.3),p(7.5,-5.4,8.4),p(-7.5,-5.4,8.4)]
    for face,normal in [([0,1,5,4],Y),([2,3,7,6],-Y),([1,2,6,5],X),([3,0,4,7],-X),([4,5,6,7],N),([3,2,1,0],-Z)]:m.polygon('housing',[pts[i] for i in face],normal)
    box((0,0,6.35),(15.05,11.52,.26),'housing',.10,axes=(X,B,N))
    box((.45,.8,6.42-.38*.8),(13.6,7.65,.36),'black',.16,axes=(X,B,N))
    # Twenty-four real key caps on a sloped deck. Their legends share one material/texture.
    for i,(label,color) in enumerate(keys):
        col=i%6;row=i//6;x=-5.14+col*2.22;depth=-1.72+row*1.73
        z=6.42-.38*depth
        center=p(x,depth,z)+N*.25
        start=len(m.polygons['keys'])
        G.bevel_box(m,center,(X,B,N),(1.88,1.37,.36),{'default':'black','+z':'keys'},bevel=.09 if lod<2 else .001)
        for index in range(start,len(m.polygons['keys'])):
            points,normal=m.polygons['keys'][index]
            uv=[]
            for q in points:
                delta=q-center
                u=np.clip(np.dot(delta,X)/1.88+.5,0,1);v=np.clip(np.dot(delta,B)/1.37+.5,0,1)
                # Atlas rows are counted down from the top; OBJ V runs upward.
                uv.append(((i%8+u)/8,1-(i//8+v)/8))
            m.polygon_uvs[('keys',index)]=uv
    # Back display: a recessed VFD lens, not an illuminated billboard.
    box((2,-4.75,9.42),(9.6,1.28,2.9),'housing',.17)
    box((2,-4.02,9.47),(8.68,.16,1.99),'black',.09)
    panel(p(2,-3.922,9.47),X,Z,8.30,1.65,'display')
    # Printer module and narrow receipt slot to the left of the display.
    box((-5.38,-3.78,8.77),(3.25,3.0,2.31),'housing',.17)
    box((-5.38,-2.20,9.1),(2.8,.20,.23),'black',.045)
    # Folded thermal paper; dual-sided geometry, slight curl, quiet printed detail.
    if lod<2:
        paper=[(-2.05,9.19),(-1.9,10.25),(-1.8,11.3),(-1.3,11.65),(-.8,11.6)]
        for k in range(len(paper)-1):
            d0,z0=paper[k];d1,z1=paper[k+1]
            q=[p(-6.65,d0,z0),p(-4.1,d0,z0),p(-4.1,d1,z1),p(-6.65,d1,z1)]
            uv=[(0,k/(len(paper)-1)),(1,k/(len(paper)-1)),(1,(k+1)/(len(paper)-1)),(0,(k+1)/(len(paper)-1))]
            m.polygon('receipt',q,uv=uv,both_sides=True)
    # Serial/badge strip on the housing face; actual intake slots down its right side.
    panel(p(-.5,5.423,3.93),X,Z,4.8,.36,'badge')
    if lod<2:
        for depth in np.linspace(-3.7,1.2,9):
            box((7.515,float(depth),4.55),(.025,.19,.8),'black',.012)
        for x in (-7.1,7.1):
            for depth in (-4.9,4.9):cyl((x,depth,3.6),Z,.05,.12,'steel')
    if lod==0:
        for x in (-7.55,7.55):
            for depth in (-4.8,4.7):
                box((x,depth,2.4),(.035,.08,.24),'steel',.009)
    # Stable local projection for housing wear. Key legends/paper/display retain custom UVs.
    for paint,polys in m.polygons.items():
        for index,(points,normal) in enumerate(polys):
            if (paint,index) in m.polygon_uvs:continue
            if abs(normal[2])>.6:uv=[((q[0]+8)/16,(-q[1]+6)/12) for q in points]
            elif abs(normal[0])>.7:uv=[((-q[1]+6)/12,q[2]/12) for q in points]
            else:uv=[((q[0]+8)/16,q[2]/12) for q in points]
            m.polygon_uvs[(paint,index)]=uv
    m.material_overrides={paint:f'{MAT}/{paint}.vmat' for paint in m.polygons}
    m.tile_overrides={paint:12 for paint in m.polygons}
    return m

counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'register_lod{lod}.obj',model(lod),f'register_lod{lod}'))
K.write_vmdl(MODEL/'register.vmdl',RES,'register_lod0',model())
text=(MODEL/'register.vmdl').read_text();start=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=text.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/register_lod{i}.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {t} meshes = ["lod{i}"] }},' for i,t in enumerate((0,10,25)))
(MODEL/'register.vmdl').write_text(text[:start]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+text[end:])
old=K.Model();R.obox(old,np.array((0.,0.,6.)),(1,0,0),(16,12,12),'rs_dark');R.configure(old);K.write_model(MODEL,RES,'legacy_register',old)
absolute=K.Model();R.obox(absolute,np.array((120.,935.,66.)),(1,0,0),(16,12,12),'rs_dark');R.configure(absolute);K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_register')
def records(path):
    lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';result=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,result
_,original=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(k for _,k in original)
public=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';current=public.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',current):
    candidate=ROOT/'Assets'/resource
    if not candidate.exists():continue
    lines,faces=records(candidate);available=collections.Counter(k for _,k in faces)
    if not (wanted-available):source=candidate;break
assert source,'Original register changed: inspect before replacing'
removed=set()
for index,key in faces:
    if wanted[key]:removed.add(index);wanted[key]-=1
assert len(removed)==12 and not +wanted
(MODEL/'store_without_register.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_register.mtl'))
(MODEL/'store_without_register.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_register.vmdl').write_text(current.replace(str(source.relative_to(ROOT/'Assets')).replace('\\','/'),RES+'/store_without_register.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(preview_only=True,triangles=counts,removed_original_triangles=12,position=[935,-120,60],original_collision=False,source_model=str(source.relative_to(ROOT)).replace('\\','/'),source_sha256=sha(source),source_vmdl=str(public.relative_to(ROOT)).replace('\\','/'),source_vmdl_sha256=sha(public),files={str(p.relative_to(REVIEW)).replace('\\','/'):sha(p) for folder in (MODEL,MATERIAL) for p in folder.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
