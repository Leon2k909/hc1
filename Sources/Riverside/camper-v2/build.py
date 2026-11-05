"""Stage the approved camper LODs/materials; import through the editor. Never regenerate Riverside."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,re,sys
import numpy as np
from PIL import Image,ImageFilter
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
OUT=ROOT/'output/riverside/camper-v2';STAGE=OUT/'stage'
RES='models/props/riverside/camper_v2';MAT='materials/riverside/camper_v2'
MODEL=STAGE/'Assets'/RES;MATERIAL=STAGE/'Assets'/MAT
for d in (MODEL,MATERIAL):d.mkdir(parents=True,exist_ok=True)
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))
rng=np.random.default_rng(30461)
def texture(name,base,rough,size=1024,wood=False):
    def noise(w,h):
        return np.asarray(Image.fromarray(rng.integers(0,256,(h,w),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),np.float32)/255
    cloud=noise(17,23);fine=noise(430,430);run=noise(180,9)
    u,v=np.meshgrid(np.linspace(0,1,size),np.linspace(1,0,size))
    if wood:
        grain=noise(240,7);lines=.5+.5*np.sin(u*math.pi*210+(cloud-.5)*8)
        dirt=(.24*cloud+.16*grain+.08*lines)
        color=np.array(base)[None,None,:]*(.62+dirt[...,None])
        height=(grain-.5)*.055+(lines-.5)*.007
    else:
        dirt=(1-v)**4*(.35+.65*cloud)+.15*run
        color=np.array(base)[None,None,:]+(cloud[...,None]-.5)*15+(fine[...,None]-.5)*5-dirt[...,None]*np.array((39,37,30))
        height=(fine-.5)*.003+(cloud-.5)*.012
    Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/f'{name}_color.png')
    Image.fromarray((np.clip(rough+.09*cloud+.07*dirt,0,1)*255).astype('uint8')).save(MATERIAL/f'{name}_rough.png')
    dy,dx=np.gradient(height);normal=np.stack((-dx*5,-dy*5,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    Image.fromarray(((normal+1)*127.5).clip(0,255).astype('uint8')).save(MATERIAL/f'{name}_normal.png')
texture('rubber',(40,39,35),.85,512)
def material(name,color,rough=.5,metal=0,textured=False):
    c=f'{MAT}/{name}_color.png' if textured else '['+' '.join(map(str,(*color,0)))+']'
    normal=f'{MAT}/{name}_normal.png' if textured else 'materials/default/default_normal.tga'
    r=f'{MAT}/{name}_rough.png' if textured else f'[{rough} {rough} {rough} 0]'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor "{c}"
 TextureNormal "{normal}"
 TextureRoughness "{r}"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
}}
''')
material('rubber',None,textured=True)
# Preserve Riverside's weathered finish instead of making the abandoned camper look factory-new.
for name,source in (('shell','rs_siding_white'),('wood','rs_wood'),('stripe','rs_red_stripe'),('chassis','rs_rust')):
    (MATERIAL/f'{name}.vmat').write_bytes((ROOT/f'Assets/materials/riverside/{source}.vmat').read_bytes())
for name in ('shell','wood','chassis'):
    for suffix in ('color','rough','normal'):
        stale=MATERIAL/f'{name}_{suffix}.png'
        if stale.exists():stale.unlink()
material('trim',(.36,.38,.35),.36,.88)
material('wheel',(.43,.42,.35),.61,.3)
material('seal',(.015,.018,.016),.82)
material('red',(.34,.012,.008),.24,.15)
material('amber',(.42,.16,.012),.3,.1)
(MATERIAL/'glass.vmat').write_text('''Layer0
{
 shader "shaders/glass.shader"
 F_GLASS_QUALITY 2
 g_bFogEnabled 1
 g_flBlurAmount 0
 g_flRefractionStrength 1.002
 AlbedoAbsorption 0.05
 TextureColor "[0.8 0.85 0.8 0]"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[0.13 0.13 0.13 0]"
 TextureMetalness "[0 0 0 0]"
 TextureAmbientOcclusion "[1 1 1 0]"
 TextureBlendMask "materials/default/default_blend.tga"
 TextureTintMask "materials/default/default.tga"
 TextureTranslucency "materials/default/default_trans.tga"
}
''')

from riverside_camper import make

counts=[];models=[]
for lod in range(3):
    model=make(lod);models.append(model);counts.append(K.write_obj(MODEL/f'camper_lod{lod}.obj',model,f'camper_lod{lod}'))
K.write_vmdl(MODEL/'camper.vmdl',RES,'camper_lod0',models[0])
doc=(MODEL/'camper.vmdl').read_text();start=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=doc.index('\n\t\t\t},',start)+len('\n\t\t\t},')
files='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/camper_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,40,110)))
(MODEL/'camper.vmdl').write_text(doc[:start]+f'{{ _class = "RenderMeshList" children = [ {files} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[end:])
manifest=dict(installed=True,triangles=counts,resource=RES+'/camper.vmdl',
              files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'build-manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))
