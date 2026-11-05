"""Full RTG crane rebuild for native review. Stage outside Assets; saved maps are untouched."""
from pathlib import Path
import sys,math,json,hashlib,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
OUT=ROOT/'output/boxyard/gantry-crane-v1';STAGE=OUT/'stage/Assets'
RES='models/props/boxyard/gantry_crane_v1';MAT='materials/boxyard/gantry_crane_v1'
MOD=STAGE/RES;MATS=STAGE/MAT
for p in (MOD,MATS):p.mkdir(parents=True,exist_ok=True)
X=np.array((1.,0,0));Y=np.array((0.,1.,0));Z=np.array((0.,0.,1.))
rng=np.random.default_rng(734825)
size=1024
def noise(w,h):return np.asarray(Image.fromarray(rng.integers(0,256,(h,w),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
cloud=noise(30,45);grain=noise(512,512);drips=noise(360,9)
u,v=np.meshgrid(np.linspace(0,1,size),np.linspace(1,0,size))
wear=np.clip((cloud-.82)*7,0,1)*np.clip((1-v)**9+.02,0,1)
for name,base in [('yellow',(201,156,31)),('red',(163,47,31)),('white',(183,189,177)),('steel',(82,89,84)),('rubber',(32,34,32))]:
    tex=np.array(base)[None,None,:]*(.96+.055*cloud[...,None])+(grain[...,None]-.5)*2
    if name!='rubber':tex=tex*(1-wear[...,None]*.6)+np.array((78,39,18))*wear[...,None]*.6-drips[...,None]*2
    Image.fromarray(tex.clip(0,255).astype('uint8')).save(MATS/f'{name}_color.png')
    Image.fromarray(((.54 if name!='rubber' else .83)+cloud*.12+wear*.17).clip(0,1).__mul__(255).astype('uint8')).save(MATS/f'{name}_rough.png')
    (MATS/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor "{MAT}/{name}_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "{MAT}/{name}_rough.png"
 g_flMetalness "{.65 if name=='steel' else .12 if name!='rubber' else 0}"
 g_vColorTint "[1 1 1 1]"
}}
''')
# Real labels/stripe panels read at the crane's architectural scale.
atlas=Image.new('RGB',(1024,512),(205,193,142));draw=ImageDraw.Draw(atlas)
try:font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',80);small=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30)
except OSError:font=small=ImageFont.load_default()
draw.rectangle((0,0,1024,256),fill=(44,49,47));draw.text((48,42),'YARD  03',font=font,fill=(218,214,183));draw.text((50,157),'RUBBER TYRED GANTRY  /  40 t',font=small,fill=(188,190,171))
for x in range(-512,1536,84):draw.polygon([(x,512),(x+56,512),(x+312,256),(x+256,256)],fill=(31,36,33))
atlas.save(MATS/'markings.png')
(MATS/'markings.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 TextureColor "{MAT}/markings.png"
 TextureRoughness "[0.7 0.7 0.7 0]"
}}
''')
# Opaque dark safety glazing preserves the existing backdrop's cheap glass treatment.
for name,col,rough,metal in [('glass',(.055,.11,.135),.16,.15),('cable',(.025,.03,.027),.8,.1),('lamp',(.65,.68,.57),.25,.2)]:
    (MATS/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor "[{' '.join(map(str,col))} 0]"
 TextureRoughness "[{rough} {rough} {rough} 0]"
 g_flMetalness "{metal}"
}}
''')

from boxyard_gantry import model

counts=[];models=[]
for lod in range(3):
    m=model(lod);models.append(m);counts.append(K.write_obj(MOD/f'gantry_lod{lod}.obj',m,f'gantry_lod{lod}'))
K.write_vmdl(MOD/'gantry.vmdl',RES,'gantry_lod0',models[0])
doc=(MOD/'gantry.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/gantry_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,100,250)))
(MOD/'gantry.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
for idx in range(1,4):
    identifier=f'{idx:02}';variant=(MOD/'gantry.vmdl').read_text().replace(f'{MAT}/markings.vmat',f'{MAT}/markings_{identifier}.vmat')
    if idx==3:variant=variant.replace(f'{MAT}/yellow.vmat',f'{MAT}/red.vmat')
    (MOD/f'gantry_{identifier}.vmdl').write_text(variant)
    atlas=Image.new('RGB',(1024,512),(205,193,142));draw=ImageDraw.Draw(atlas)
    draw.rectangle((0,0,1024,256),fill=(44,49,47));draw.text((48,42),f'YARD  {identifier}',font=font,fill=(218,214,183));draw.text((50,157),'RUBBER TYRED GANTRY  /  40 t',font=small,fill=(188,190,171))
    for x in range(-512,1536,84):draw.polygon([(x,512),(x+56,512),(x+312,256),(x+256,256)],fill=(31,36,33))
    atlas.save(MATS/f'markings_{identifier}.png')
    (MATS/f'markings_{identifier}.vmat').write_text((MATS/'markings.vmat').read_text().replace('markings.png',f'markings_{identifier}.png'))
manifest=dict(installed=True,triangles=counts,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'build-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'triangles':counts,'variants':3}))
