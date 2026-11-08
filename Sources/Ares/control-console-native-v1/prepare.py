"""Native adaptation of the existing private Ares console proposal; no new geometry authored."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,re,shutil
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
LEGACY=ROOT/'Sources/Ares/control-console-trial-v1';OUT=ROOT/'output/ares/control-console-native-v1';STAGE=OUT/'stage/Assets';RES='models/props/ares/control_console_native_v1';MAT='materials/ares/control_console_native_v1';MODEL=STAGE/RES;MATS=STAGE/MAT
for d in (MODEL,MATS):d.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# MTL values and authored PBR maps are retained; the approved screen uses its current original material.
materials={};name=None
for line in (LEGACY/'control_console_after.mtl').read_text().splitlines():
    p=line.split()
    if not p:continue
    if p[0]=='newmtl':name=p[1];materials[name]={}
    elif name:materials[name][p[0]]=p[1:]
bindings={};texture_inputs=[]
for name,data in materials.items():
    if name=='Original_approved_Ares_display_atlas':bindings[name]='materials/ares/ar_screens.vmat';continue
    paint=re.sub('[^a-z0-9]+','_',name.lower());bindings[name]=f'{MAT}/{paint}.vmat'
    def texture(key,default):
        if key not in data:return default
        relative=data[key][-1];src=LEGACY/relative;dest=MATS/src.name;shutil.copyfile(src,dest);texture_inputs.append(src);return f'{MAT}/{src.name}'
    color=texture('map_Kd','['+' '.join(data.get('Kd',['.5','.5','.5']))+' 1]')
    rough=texture('map_Ns','[0.55 0.55 0.55 0]');normal=texture('map_Bump','materials/default/default_normal.tga');metal=.96 if 'stainless' in name.lower() else 0
    text=f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 TextureColor "{color}"
 TextureNormal "{normal}"
 TextureRoughness "{rough}"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "1"
 g_flModelTintAmount "1"
'''
    emission=list(map(float,data.get('Ke',['0','0','0'])))
    if max(emission)>0:
        text+=' F_SELF_ILLUM "1"\n TextureSelfIllumMask "[1 1 1 0]"\n g_flSelfIllumBrightness "1"\n g_flSelfIllumAlbedoFactor "0"\n g_vSelfIllumTint "['+' '.join(map(str,emission))+' 0]"\n'
    (MATS/f'{paint}.vmat').write_text(text+'}\n')
lines=[];triangles=0
for line in (LEGACY/'control_console_after.obj').read_text().splitlines():
    if line.startswith('v '):
        x,y,z=map(float,line.split()[1:]);line=f'v {x/0.0254:.6f} {z/0.0254:.6f} {-y/0.0254:.6f}'
    elif line.startswith('vn '):
        x,y,z=map(float,line.split()[1:]);line=f'vn {x:.7f} {z:.7f} {-y:.7f}'
    elif line.startswith('mtllib '):line='mtllib console.mtl'
    elif line.startswith('f '):triangles+=1;assert len(line.split())==4
    lines.append(line)
(MODEL/'console.obj').write_text('\n'.join(lines)+'\n');(MODEL/'console.mtl').write_text('\n'.join(f'newmtl {name}\nKd 1 1 1\nd 1' for name in materials)+'\n')
m=K.Model();m.polygons={name:[] for name in materials};m.material_overrides.update(bindings);K.write_vmdl(MODEL/'console.vmdl',RES,'console',m)
if '--assets-only' in sys.argv:
    print('Base assets staged. Run build_lods.py with Blender next.');raise SystemExit(0)
# Match the frozen exact current baseline against the active render import, including newer accepted imports.
before=json.loads((LEGACY/'before.json').read_text());origin=np.array((230.,-440.,0.));wanted=Counter()
for paint,faces in before.items():
    for face in faces:
        pts=np.array(face['vertices'])+origin;obj=[(-p[0],p[2],p[1]) for p in pts];wanted[(paint,tuple(sorted(tuple(round(float(x),3) for x in p) for p in obj)))]+=1
assert sum(wanted.values())==40
docpath=ROOT/'Assets/models/maps/ares/ares_dressing.vmdl';doc=docpath.read_text();imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',doc);matches=[]
for relative in imports:
    src=ROOT/'Assets'/relative;raw=src.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in raw if l.startswith('v ')];paint='';cut=set();remaining=wanted.copy()
    for i,line in enumerate(raw):
        if line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            key=(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:])))
            if remaining[key]:remaining[key]-=1;cut.add(i)
    if len(cut)==40 and not +remaining:matches.append((relative,raw,cut))
assert len(matches)==1,'Current console is different or already upgraded'
relative,raw,cut=matches[0];(MODEL/'preview.obj').write_text(''.join(line for i,line in enumerate(raw) if i not in cut))
for name in re.findall(r'^mtllib (.+)$',''.join(raw),re.M):shutil.copyfile((ROOT/'Assets'/relative).parent/name.strip(),MODEL/name.strip())
(MODEL/'preview.vmdl').write_text(doc.replace(relative,f'{RES}/preview.obj'))
protected=[docpath,ROOT/'Assets/scenes/maps/Ares/ares.scene',*[ROOT/'Assets'/p for p in imports],LEGACY/'control_console_after.obj',LEGACY/'control_console_after.mtl',LEGACY/'before.json',*set(texture_inputs)]
manifest=dict(preview_only=True,reused_existing_candidate=str(LEGACY.relative_to(ROOT)).replace('\\','/'),triangles=triangles,lods=1,original_faces=40,active_base=relative,cut=sorted(cut),position_world=[-440.,-230.,0.],
 protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected},files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'reused_existing_candidate':True,'triangles':triangles,'materials':len(materials),'old_faces':40,'active_base':relative}))
