"""Reuse the approved Ares sign construction for the main concourse airlock lightbox."""
from pathlib import Path
from collections import Counter
import sys,json,re,hashlib,shutil,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A,map_kit as K,ares_observation_sign as O
OUT=ROOT/'output/ares/main-airlock-sign-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/main_airlock_sign_v1';MAT='materials/ares/main_airlock_sign_v1';DEST=STAGE/RES;MD=STAGE/MAT
for d in (DEST,MD):d.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();center=np.array((0.,-1398.5,250.))
old=K.Model();A.lit_sign(old,'airlock07',center,(0,1),128,32);A.configure(old);K.write_obj(OUT/'expected.obj',old,'expected')
def sigs(lines):
 v=[];paint='';result=[]
 for i,l in enumerate(lines):
  s=l.split()
  if not s:continue
  if s[0]=='v':v.append(tuple(round(float(x),3) for x in s[1:]))
  elif s[0]=='usemtl':paint=s[1]
  elif s[0]=='f':result.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in s[1:])))))
 return result
wanted=Counter(k for i,k in sigs((OUT/'expected.obj').read_text().splitlines()));assert sum(wanted.values())==14
docpath=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for rel in imports:
 lines=(ROOT/'Assets'/rel).read_text().splitlines(keepends=True);remaining=wanted.copy();cut=[]
 for i,k in sigs(lines):
  if remaining[k]:remaining[k]-=1;cut.append(i)
 if len(cut)==14 and not +remaining:matches.append((rel,lines,cut))
assert len(matches)==1,'Current main-airlock sign differs from baseline'
rel,lines,cut=matches[0];(DEST/'preview.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(lines),re.M):shutil.copyfile((ROOT/'Assets'/rel).parent/name.strip(),DEST/name.strip())
(DEST/'preview.vmdl').write_text(doc.replace(rel,RES+'/preview.obj'))
# Reuse the accepted manufactured enclosure, retaining its seams, vents and fasteners.
source=O.model();m=K.Model();T=np.diag((-130/194,-.5,34/50));N=np.linalg.inv(T).T;source_center=np.array((0.,600.,420.));omitted=0
for paint,rows in source.polygons.items():
 for i,(points,normal) in enumerate(rows):
  p=np.array(points)
  hanging=p[:,2].min()>=443.99 and (np.all(np.abs(p[:,0]-80)<=4.001) or np.all(np.abs(p[:,0]+80)<=4.001))
  if hanging:omitted+=len(points)-2;continue
  ns=source.polygon_normals.get((paint,i));m.polygon(paint,[center+T@(q-source_center) for q in p],N@normal,uv=source.polygon_uvs.get((paint,i)),normals=[N@n for n in ns] if ns is not None else None)
m.material_overrides.update(source.material_overrides);m.material_overrides['face']=MAT+'/face.vmat';m.tile_overrides.update(source.tile_overrides)
K.write_obj(DEST/'sign.obj',m,'sign');K.write_vmdl(DEST/'sign.vmdl',RES,'sign',m)
# Text/diagram artwork follows the approved observation-sign typography and palette.
image=Image.new('RGB',(2048,512),(21,28,31));mask=Image.new('L',image.size,0);draw=ImageDraw.Draw(image);glow=ImageDraw.Draw(mask);font_path=ROOT/'Assets/fonts/Dinish-Bold.ttf'
def label(at,text,size,color,emission):
 font=ImageFont.truetype(str(font_path),size);draw.text(at,text,font=font,fill=color,anchor='lt');glow.text(at,text,font=font,fill=emission,anchor='lt')
draw.rectangle((48,44,61,466),fill=(162,65,40));glow.rectangle((48,44,61,466),fill=25)
label((98,52),'ARES  /  FACILITY',45,(155,170,166),35)
size=235
while ImageFont.truetype(str(font_path),size).getlength('AIRLOCK 07')>1580:size-=1
label((92,137),'AIRLOCK 07',size,(227,232,222),220)
draw.line((98,379,1940,379),fill=(66,82,82),width=3);label((99,412),'CONTROLLED ACCESS',40,(148,164,159),30)
draw.ellipse((1756,168,1940,352),outline=(185,202,193),width=8);glow.ellipse((1756,168,1940,352),outline=80,width=8)
draw.line((1848,190,1848,330),fill=(185,202,193),width=5);draw.rectangle((1822,254,1874,266),fill=(185,202,193));glow.line((1848,190,1848,330),fill=80,width=5);glow.rectangle((1822,254,1874,266),fill=80)
image.save(MD/'face_color.png');mask.save(MD/'face_illum.png')
(MD/'face.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "'''+MAT+'''/face_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[0.62 0.62 0.62 0]"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flMetalness "0"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
 F_SELF_ILLUM "1"
 TextureSelfIllumMask "'''+MAT+'''/face_illum.png"
 g_flSelfIllumBrightness "1.6"
 g_flSelfIllumAlbedoFactor "1"
 g_vSelfIllumTint "[1 0.98 0.92 0]"
}
''')
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',*[ROOT/'Assets'/p for p in imports],ROOT/'Tools/ares_observation_sign.py',font_path]
for path in set(source.material_overrides.values())|{'materials/ares/ar_signs_lit.vmat'}:
 p=ROOT/'Assets'/path;protected.append(p)
 for texture in re.findall(r'Texture\w+\s+"([^\"]+)"',p.read_text()):
  q=ROOT/'Assets'/texture
  if q.is_file():protected.append(q)
manifest=dict(review_only=True,reused_approved_sign_construction=True,original_faces=14,triangles=m.triangle_count(),suspension_triangles_omitted=omitted,original_outer_width_height=[130,34],active_base=rel,cut=cut,protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k not in ('protected','files','cut')}))
