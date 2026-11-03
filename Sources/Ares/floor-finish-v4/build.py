"""A floor-material and UV-only overlay on the constructed Ares review."""
from pathlib import Path
import json,hashlib,shutil,sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S,map_kit as K
OUT=ROOT/'output/ares/floor-finish-v4';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'output/ares/constructed-interior-v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,text):
    p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
manifest=json.loads((BASE/'manifest.json').read_text())
for p,h in manifest['guards'].items():assert sha(ROOT/p)==h,'Published input changed: '+p
source=BASE/'stage/Assets/models/maps/ares/constructed-v3/hall.obj'
header,faces=S.read_obj(source);out=[];offset=K.uv_offset('ares_hall');changed=0
for paint,corners in faces:
    if paint=='ar_floor':
        corners=tuple((p,' '.join(f'{(float(v)-offset[i])*192/80+offset[i]:.6f}' for i,v in enumerate(uv.split())),n) for p,uv,n in corners)
        changed+=1
    out.append((paint,corners))
assert changed>10
assert len(out)==len(faces)
assert Counter(tuple((p,n) for p,uv,n in c) for m,c in faces)==Counter(tuple((p,n) for p,uv,n in c) for m,c in out)
folder='Assets/models/maps/ares/floor-finish-v4/'
p=STAGE/folder/'hall.obj';p.parent.mkdir(parents=True,exist_ok=True)
S.write_obj(p,header,out)
put(folder+'hall.mtl',(BASE/'stage/Assets/models/maps/ares/constructed-v3/hall.mtl').read_text())
doc=(BASE/'stage/Assets/models/maps/ares/constructed-v3/ares_hall_trial.vmdl').read_text()
original=doc
doc=doc.replace('models/maps/ares/constructed-v3/hall.obj','models/maps/ares/floor-finish-v4/hall.obj',1)
doc=doc.replace('materials/ares/constructed-v3/floor.vmat','materials/ares/floor-finish-v4/plate.vmat')
doc=doc.replace('materials/ares/ar_floor.vmat','materials/ares/floor-finish-v4/grip.vmat')
marker='_class = "PhysicsShapeList"';assert doc[doc.index(marker):]==original[original.index(marker):]
put(folder+'ares_hall_trial.vmdl',doc)
for name in ('plate','grip'):
    tint='0.65 0.65 0.65 1' if name=='grip' else '1 1 1 1'
    put('Assets/materials/ares/floor-finish-v4/'+name+'.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0.08"
 g_flRoughnessScaleFactor "1"
 TextureColor "materials/ares/floor-finish-v4/{name}_color.png"
 TextureNormal "materials/ares/floor-finish-v4/{name}_normal.png"
 TextureRoughness "materials/ares/floor-finish-v4/{name}_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint}]"
 g_flModelTintAmount "1"
}}
''')
report=dict(guards=manifest['guards'],preview_input=dict(path=source.relative_to(ROOT).as_posix(),sha256=sha(source)),
 files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
 floor_uv_faces=changed,face_count=len(faces),positions_normals_and_collision_unchanged=True,gallery_tile_inches=80)
(OUT/'manifest.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('guards','files','preview_input')},indent=2))
