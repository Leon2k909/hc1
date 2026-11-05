"""Review-only replacement for Lucky Stop's two flat fluorescent fixture boxes."""
from pathlib import Path
import sys,json,hashlib,collections,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/fluorescent-v1';STAGE=OUT/'stage'
RES='models/props/riverside/fluorescent_v1';MAT='materials/riverside/fluorescent_v1'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
for p in (OUT,MODEL,MATERIAL):p.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(55323);size=1024;yy,xx=np.mgrid[0:size,0:size]/(size-1)
def noise(n):return np.asarray(Image.fromarray(rng.integers(0,256,(n,n),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
n=noise(14);f=noise(320)
edge=np.exp(-np.minimum(xx,1-xx)*95);dirt=(1-yy)**5*(.3+.7*n)
color=np.zeros((size,size,3))+[181,186,171];color+=(n[...,None]-.5)*11+(f[...,None]-.5)*3
color-=dirt[...,None]*[25,23,19];chips=(rng.random((size,size))<(.027*edge+.0004))&(f>.46);color[chips]=[99,82,57]
Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/'paint_color.png')
Image.fromarray(((.51+.19*dirt+.10*f)*255).clip(0,255).astype('uint8')).save(MATERIAL/'paint_rough.png')
ty,tx=np.mgrid[0:1024,0:128]/np.array((1023,127))[:,None,None]
ends=np.exp(-np.minimum(ty,1-ty)*45)
tube=np.zeros((1024,128,3))+[201,214,219];tube-=ends[...,None]*[104,108,106]
tube+=(rng.random((1024,128,1))-.5)*2
Image.fromarray(tube.clip(0,255).astype('uint8')).save(MATERIAL/'tube_color.png')
Image.fromarray(((.95-.82*ends)*255).clip(0,255).astype('uint8')).save(MATERIAL/'tube_glow.png')
label=Image.new('RGB',(1024,256),(177,172,142));d=ImageDraw.Draw(label)
for y,text,s in [(16,'2 x T8  /  120 V  /  60 Hz',61),(111,'DISCONNECT SUPPLY BEFORE SERVICING',37),(181,'RAPID START — INDOOR USE',34)]:
    d.text((512,y),text,anchor='mt',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',s),fill=(49,56,50))
label.save(MATERIAL/'label_color.png')
def material(name,color,rough=.5,metal=0,emission=0):
    c=f'"{MAT}/{color}"' if isinstance(color,str) else '"['+' '.join(map(str,(*color,0)))+']"'
    extra=f'TextureRoughness "[{rough} {rough} {rough} 0]"'
    if name=='paint':extra=f'TextureRoughness "{MAT}/paint_rough.png"'
    if emission:extra+=f'\n F_SELF_ILLUM 1\n TextureSelfIllumMask "{MAT}/tube_glow.png"\n g_flSelfIllumBrightness "{emission}"\n g_flSelfIllumAlbedoFactor "1"\n g_vSelfIllumTint "[1 1 1 1]"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {c}
 TextureNormal "materials/default/default_normal.tga"
 {extra}
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[1 1 1 1]"
}}
''')
material('paint','paint_color.png',.6)
material('tube','tube_color.png',.3,emission=4)
material('steel',(.31,.35,.34),.34,.88)
material('socket',(.21,.23,.19),.76)
material('dark',(.018,.024,.020),.9)
material('label','label_color.png',.8)
X=np.array((1.,0,0));Y=np.array((0.,1,0));Z=np.array((0.,0,1.))
def make(lod):
    m=K.Model();sides=(24,14,8)[lod]
    def box(c,s,paint='paint',b=0):
        if b and lod<2:G.bevel_box(m,np.asarray(c),(X,Y,Z),s,paint,b)
        else:m.oriented_box(np.asarray(c),(X,Y,Z),s,paint)
    def axis(c,profile,paint,along=Y):G.lathe_axis(m,np.asarray(c),along,profile,paint,sides=sides)
    # Thin folded tray with real depth: the reflector opens down toward the shop floor.
    box((0,0,2.62),(7.7,47.7,.48),'paint',.13)
    for side in (-1,1):
        pts=[np.array((side*.75,-22,2.37)),np.array((side*3.8,-22,.65)),np.array((side*3.8,22,.65)),np.array((side*.75,22,2.37))]
        m.polygon('paint',pts if side==1 else list(reversed(pts)),both_sides=True)
        box((side*3.88,0,1.47),(.22,47.5,2.7),'paint',.08)
    for y in (-23.55,23.55):box((0,y,1.55),(7.55,.28,2.5),'paint',.09)
    box((0,0,2.14),(1.35,36,.38),'paint',.08)
    # Two cylindrical phosphor tubes, separated from their holders and metal end caps.
    for x in (-1.9,1.9):
        before=len(m.polygons['tube'])
        axis((x,-21.8,.71),[(0,0),(.48,0),(.52,.18),(.52,43.42),(.48,43.6),(0,43.6)],'tube')
        for i in range(before,len(m.polygons['tube'])):
            pts,normal=m.polygons['tube'][i]
            m.polygon_uvs[('tube',i)]=[((p[0]-x+0.53)/1.06,(p[1]+21.8)/43.6) for p in pts]
        for end in (-1,1):
            y=end*21.8
            axis((x,y-.38,.71),[(0,0),(.535,0),(.535,.76),(0,.76)],'steel')
            box((x,end*22.65,1.03),(1.28,.94,1.55),'socket',.16)
            if lod<2:
                for dx in (-.22,.22):
                    axis((x+dx,end*22.13,.71),[(0,0),(.06,0),(.06,.42),(0,.42)],'steel')
    # Spring catches, mounting tabs and a small ballast access label are actual separate pieces.
    for y in (-18,18):
        box((0,y,3.0),(3.0,1.2,.2),'steel',.04)
        box((0,y,3.775),(.55,.55,1.55),'steel')
        box((0,y,4.50),(3.2,2.2,.20),'steel')
        if lod<2:
            axis((0,y,2.92),[(0,0),(.20,0),(.20,.18),(0,.18)],'steel',Z)
    G.quad(m,'label',np.array((0.,1.5,1.94)),Y,X,8.5,1.25,uv=[(0,0),(1,0),(1,1),(0,1)])
    if lod==0:
        for x in (-3.35,3.35):
            for y in (-22.8,22.8):
                axis((x,y,2.34),[(0,0),(.16,0),(.16,.06),(0,.06)],'steel',-Z)
                box((x,y,2.272),(.22,.038,.012),'dark')
        # A restrained yellowed seam where dust collects, rather than uniformly rusty metal.
        for side in (-1,1):box((side*3.76,0,2.24),(.065,43.8,.10),'dark')
    for paint,polys in m.polygons.items():
        for i,(pts,normal) in enumerate(polys):
            if (paint,i) in m.polygon_uvs:continue
            if abs(normal[2])>.65:uv=[((p[0]+4)/8,(p[1]+24)/48) for p in pts]
            elif abs(normal[0])>.65:uv=[((p[1]+24)/48,p[2]/3.1) for p in pts]
            else:uv=[((p[0]+4)/8,p[2]/3.1) for p in pts]
            m.polygon_uvs[(paint,i)]=uv
    m.material_overrides={p:f'{MAT}/{p}.vmat' for p in m.polygons};m.tile_overrides={p:48 for p in m.polygons}
    return m
counts=[]
for lod in range(3):counts.append(K.write_obj(MODEL/f'fixture_lod{lod}.obj',make(lod),f'fixture_lod{lod}'))
K.write_vmdl(MODEL/'fixture.vmdl',RES,'fixture_lod0',make(0))
text=(MODEL/'fixture.vmdl').read_text();a=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=text.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/fixture_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,12,30)))
(MODEL/'fixture.vmdl').write_text(text[:a]+f'{{ _class = "RenderMeshList" children = [{files}] }},\n{{ _class = "LODGroupList" children = [{groups}] }},'+text[b:])
old=K.Model();R.obox(old,np.array((0.,0.,1.6)),(0,1),(48,8,3),'rs_dark')
R.card(old,'rs_lamp_cool',[np.array((-3,-23,0)),np.array((3,-23,0)),np.array((3,23,0)),np.array((-3,23,0))],-Z)
R.configure(old);K.write_model(MODEL,RES,'legacy_fixture',old)
origin=np.array((150.,R.STORE[2]+120,R.STORE_TOP-4.6))
absolute=P.place(old,origin,0);R.configure(absolute);K.write_obj(OUT/'legacy_absolute.obj',absolute,'old_fixture')
def records(p):
    lines=p.read_text().splitlines(keepends=True);vs=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];mat='';r=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):mat=l.split()[1]
        if l.startswith('f '):r.append((i,(mat,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,r
_,oldfaces=records(OUT/'legacy_absolute.obj');wanted=collections.Counter(k for _,k in oldfaces)
vmdl=ROOT/'Assets/models/maps/riverside/riverside_store.vmdl';vt=vmdl.read_text();source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vt):
    p=ROOT/'Assets'/resource
    if not p.exists():continue
    lines,faces=records(p)
    if not wanted-collections.Counter(k for _,k in faces):source=p;break
assert source,'Original fixture no longer matches current store mesh.'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==14 and not +wanted
(MODEL/'store_without_fixture.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib store_without_fixture.mtl'))
(MODEL/'store_without_fixture.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'store_without_fixture.vmdl').write_text(vt.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/store_without_fixture.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected=[source,vmdl,ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
m=dict(preview_only=True,triangles=counts,position=K.to_world(origin).tolist(),removed_old_triangles=14,resource=RES+'/fixture.vmdl',background=RES+'/store_without_fixture.vmdl',
       protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(m,indent=2));print(json.dumps({k:v for k,v in m.items() if k!='files'},indent=2))
