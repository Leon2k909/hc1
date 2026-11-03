"""Prepare a material/UV-only trial from the currently installed Ares models."""
from pathlib import Path
from collections import Counter
import hashlib, json, re, shutil, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import riverdale_splice as S
import map_kit as K
OUT=ROOT/'output/ares/surface-finish-v2'
STAGE=OUT/'stage'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(rel,content):
    p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8',newline='')
    return p
paths=['Assets/models/maps/ares/pressure-doors-v2/hall_base.obj',
       'Assets/models/maps/ares/pressure-doors-v2/hall_base.mtl',
       'Assets/models/maps/ares/ares_hall.vmdl','Assets/models/maps/ares/ares_reactor.vmdl',
       'Assets/scenes/maps/Ares/ares.scene','Tools/ares_interior.py']
guards={}
for rel in paths:
    p=ROOT/rel;backup=OUT/'before'/rel
    if backup.exists():assert sha(backup)==sha(p),f'Already changed: {rel}'
    else:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
    guards[rel]=sha(p)
header,faces=S.read_obj(ROOT/paths[0]);result=[];changed=0;offset=K.uv_offset('ares_hall')
for mat,corners in faces:
    broad=mat=='ar_in_panel' and all(1095<abs(float(p.split()[0]))<1101 and abs(float(n.split()[0]))>.99 for p,uv,n in corners)
    if broad:
        mat='ar_in_wall';changed+=1
        corners=tuple((p,' '.join(f'{(float(v)-offset[i])*.5+offset[i]:.6f}' for i,v in enumerate(uv.split())),n) for p,uv,n in corners)
    result.append((mat,corners))
assert 50<changed<2000,changed
trial='Assets/models/maps/ares/surface-finish-v2/'
p=STAGE/trial/'hall_trial.obj';p.parent.mkdir(parents=True,exist_ok=True)
header=[line.replace('hall_base.mtl','hall_trial.mtl') for line in header]
S.write_obj(p,header,result)
mtl=(ROOT/paths[1]).read_text()+'\nnewmtl ar_in_wall\nKd 1 1 1\n'
put(trial+'hall_trial.mtl',mtl)
vmat='materials/ares/surface-finish-v2/'
for model in ('hall','reactor'):
    doc=(ROOT/f'Assets/models/maps/ares/ares_{model}.vmdl').read_text()
    for name in ('floor','frame'):
        doc=doc.replace(f'materials/ares/interior-v1/{name}.vmat',vmat+name+'.vmat')
    for name in ('steel','gunmetal','grating'):
        doc=doc.replace(f'materials/ares/ar_{name}.vmat',vmat+name+'.vmat')
    if model=='hall':
        doc=doc.replace('models/maps/ares/pressure-doors-v2/hall_base.obj','models/maps/ares/surface-finish-v2/hall_trial.obj')
        doc=doc.replace('{ from = "ar_in_alloy.vmat"', '{ from = "ar_in_wall.vmat" to = "'+vmat+'wall.vmat" },\n{ from = "ar_in_alloy.vmat"',1)
    put(trial+f'ares_{model}_trial.vmdl',doc)
for name,rough in [('wall',.62),('floor',.57)]:
    put('Assets/'+vmat+name+'.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0"
 g_flRoughnessScaleFactor "{rough}"
 TextureColor "{vmat}{name}_color.png"
 TextureNormal "{vmat}{name}_normal.png"
 TextureRoughness "materials/default/default_rough.tga"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
 g_flModelTintAmount "1"
}}
''')
frame=(ROOT/'Assets/materials/ares/interior-v1/frame.vmat').read_text()
frame=re.sub(r'g_flMetalness "[^"]+"','g_flMetalness "0"',frame)
frame=frame.replace('g_vColorTint "[1 1 1 1]"','g_vColorTint "[1.35 1.35 1.35 1]"')
put('Assets/'+vmat+'frame.vmat',frame)
for name,tint in [('steel','1.65 1.65 1.65 1'),('grating','1.5 1.5 1.5 1')]:
    src='interior-v1/frame.vmat' if name=='steel' else 'ar_grating.vmat'
    text=(ROOT/f'Assets/materials/ares/{src}').read_text()
    text=re.sub(r'g_flMetalness "[^"]+"','g_flMetalness "0"',text)
    text=re.sub(r'g_vColorTint "[^"]+"',f'g_vColorTint "[{tint}]"',text)
    put('Assets/'+vmat+name+'.vmat',text)
gunmetal=(STAGE/('Assets/'+vmat+'floor.vmat')).read_text()
gunmetal=gunmetal.replace('g_vColorTint "[1 1 1 1]"','g_vColorTint "[0.72 0.78 0.85 1]"')
put('Assets/'+vmat+'gunmetal.vmat',gunmetal)
assert len(faces)==len(result)
assert Counter(tuple((p,n) for p,uv,n in c) for m,c in faces)==Counter(tuple((p,n) for p,uv,n in c) for m,c in result)
manifest={'guards':guards,'files':{str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()},
          'wall_faces_remapped':changed,'face_count':len(faces),'positions_and_normals_preserved':True,'uv_scale':192,
          'generated_source_dimensions':[1254,1254],'native_import_dimensions':[2048,2048]}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k not in ('guards','files')},indent=2))
