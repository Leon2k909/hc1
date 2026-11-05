from pathlib import Path
import sys,json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/riverside/discarded-tyres-v1';STAGE=OUT/'stage'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverside_parts as P,riverside_map as R
# Adapt the already verified hollow casing and tread construction to these smaller loose tyres.
source=(ROOT/'Tools/lowtide_tyres.py').read_text();fn=source[source.index('def tyre('):]
header='''import math,zlib
import numpy as np
import map_kit as K
PAINT='rt_tyre'
RESOURCE='materials/riverside/discarded-tyres-v1/rubber.vmat'
def configure(model):
 model.material_overrides[PAINT]=RESOURCE;model.tile_overrides[PAINT]=12
def tire(m,c,axis=(0,0,1),r=13.,w=8.,paint_name='rs_rubber'):
 assert abs(float(axis[2]))>.99, 'Loose tyres only'
 tyre(m,c[0],c[1],c[2]-w/2,r,w)
'''
detail='''
def tyre(model,e,n,z,radius=14.,width=8.):
 _casing(model,e,n,z,radius,width)
 import riverdale_parts as P
 # Moulded sidewall lettering follows the curved rubber surface.
 for k in range(64):
  aa=[2*math.pi*i/64 for i in (k,k+1)]
  for r0,h0,r1,h1 in ((.70,.96,.71,.96),(.71,.96,.78,.936),(.78,.936,.80,.925),(.80,.925,.81,.916)):
   ps=[(e+math.cos(a)*r*radius,n+math.sin(a)*r*radius,z+h*width+.028) for a,r,h in ((aa[0],r0,h0),(aa[1],r0,h0),(aa[1],r1,h1),(aa[0],r1,h1))]
   uv=[(1-k/64,(r0-.70)/.11),(1-(k+1)/64,(r0-.70)/.11),(1-(k+1)/64,(r1-.70)/.11),(1-k/64,(r1-.70)/.11)]
   P.card(model,'rt_sidewall',ps,(0,0,1),uv=uv)
 model.material_overrides['rt_sidewall']='materials/riverside/discarded-tyres-v1/sidewall.vmat'
 model.tile_overrides['rt_sidewall']=12
'''
(HERE/'tyres.py').write_text(header+fn.replace('def tyre(','def _casing(',1)+detail)
import tyres
folder=STAGE/'Assets/materials/riverside/discarded-tyres-v1';folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(31569);grain=rng.normal(0,1,(1024,1024))
col=np.array((57.,59.,54.))+grain[:,:,None]*1.8
Image.fromarray(np.clip(col,0,255).astype('uint8')).save(folder/'rubber_color.png')
Image.fromarray(np.clip(192+grain*2,0,255).astype('uint8')).save(folder/'rubber_rough.png')
dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.018;dy=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.018
n=np.stack((dx,dy,np.ones_like(grain)),2);n/=np.linalg.norm(n,axis=2)[:,:,None]
Image.fromarray(np.clip((n*.5+.5)*255,0,255).astype('uint8')).save(folder/'rubber_normal.png')
(folder/'rubber.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "materials/riverside/discarded-tyres-v1/rubber_color.png"
 TextureNormal "materials/riverside/discarded-tyres-v1/rubber_normal.png"
 TextureRoughness "materials/riverside/discarded-tyres-v1/rubber_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flMetalness "0"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
}
''')
label=Image.new('RGB',(2048,128),(57,59,54));draw=ImageDraw.Draw(label)
font=ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',55)
draw.text((45,33),'RADIAL TUBELESS    205 / 65 R15     ALL SEASON    205 / 65 R15',font=font,fill=(93,95,88))
label.save(folder/'sidewall_color.png')
(folder/'sidewall.vmat').write_text((folder/'rubber.vmat').read_text().replace('rubber_color.png','sidewall_color.png'))
modeldir=STAGE/'Assets/models/maps/riverside/discarded-tyres-v1';modeldir.mkdir(parents=True,exist_ok=True)
counts={}
for name in ('before','tyre'):
 m=K.Model()
 if name=='before':P.tire(m,(0,0,0),(0,0,1),r=12.5,w=8)
 else:tyres.tire(m,(0,0,0),(0,0,1),r=12.5,w=8)
 R.configure(m);counts[name]=K.write_obj(modeldir/(name+'.obj'),m,'riverside_dressing')
 K.write_vmdl(modeldir/(name+'.vmdl'),'models/maps/riverside/discarded-tyres-v1',name,m)
plan=dict(triangles=counts,files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in STAGE.rglob('*') if p.is_file()})
(OUT/'preview-plan.json').write_text(json.dumps(plan,indent=2));print(counts)
for name in ('import_preview.cs.txt','compile.py','capture.cs.txt'):
 text=(ROOT/'Sources/Riverside/searchlight-v1'/name).read_text().replace('searchlight-v1','discarded-tyres-v1')
 if name=='compile.py':text=text.replace("('before','searchlight')","('before','tyre')")
 if name=='capture.cs.txt':
  text=text.replace('"before","searchlight"','"before","tyre"').replace('Searchlight comparison','Discarded tyre comparison')
  text=text.replace('new Vector3(0,0,-16)','new Vector3(0,0,-4)').replace('W(60,-82,36)','W(37,-48,43)').replace('W(0,0,-1)','W(0,0,0)').replace('FieldOfView=29','FieldOfView=34')
 (HERE/name).write_text(text)
