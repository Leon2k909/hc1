from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
REVIEW=Path(__file__).resolve().parents[3]
OUT=REVIEW/'output/riverside/register-v1'
m=json.loads((OUT/'manifest.json').read_text())
runtime=json.loads((OUT/'runtime-review.json').read_text())
assert runtime['ActualPlayMode'] and runtime['PlayerCount']>0 and not runtime['ErrorModels'] and runtime['NoExtraLights']
assert json.loads((OUT/'state-restored.json').read_text())['restored']
assert runtime['PublicStore']['TotalTriangles']-runtime['StoreWithout']['TotalTriangles']==12
assert runtime['Candidate']['LodCount']==3
assert [mesh['Triangles'] for mesh in runtime['Candidate']['Meshes']]==m['triangles']
assert [mesh['LodMask'] for mesh in runtime['Candidate']['Meshes']]==[1,2,4]
public={mesh['Name']:mesh for mesh in runtime['PublicStore']['Meshes']}
without={mesh['Name']:mesh for mesh in runtime['StoreWithout']['Meshes']}
for name,mesh in public.items():
    assert mesh['LodMask']==without[name]['LodMask']
    assert mesh['Triangles']-without[name]['Triangles']==(12 if name=='riverside_store' else 0)
checks=[]
for lod,expected in enumerate(m['triangles']):
    path=REVIEW/f'Assets/models/maps/riverside/register-v1/register_lod{lod}.obj'
    vertices=[];uvs=[];normals=[];faces=[]
    for line in path.read_text().splitlines():
        if line.startswith('v '):vertices.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uvs.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):normals.append(list(map(float,line.split()[1:])))
        elif line.startswith('f '):faces.append([list(map(int,p.split('/'))) for p in line.split()[1:]])
    v=np.asarray(vertices);n=np.asarray(normals)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uvs).all()
    assert max(abs(np.linalg.norm(n,axis=1)-1))<.00087
    areas=[]
    for face in faces:
        assert len(face)==3
        for vi,ti,ni in face:assert 1<=vi<=len(v) and 1<=ti<=len(uvs) and 1<=ni<=len(n)
        a,b,c=v[[p[0]-1 for p in face]];areas.append(float(np.linalg.norm(np.cross(b-a,c-a))*.5))
    assert min(areas)>1e-8 and len(faces)==expected
    checks.append(dict(lod=lod,triangles=len(faces),minimum_triangle_area=min(areas),finite=True,indices_valid=True))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
marker='_class = "PhysicsShapeList"'
original=(ROOT/m['source_vmdl']).read_text();preview=(REVIEW/'Assets/models/maps/riverside/register-v1/store_without_register.vmdl').read_text()
assert original[original.index(marker):]==preview[preview.index(marker):]
before=Image.open(OUT/'in-game-before.png').convert('RGB');after=Image.open(OUT/'in-game-after.png').convert('RGB')
assert np.mean(abs(np.asarray(before,dtype=float)-np.asarray(after,dtype=float)))>2
# Compose native captures without any exposure/color adjustment.
sheet=Image.new('RGB',(1600,692),'#111416');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
for x,image,title,detail in [(0,before,'CURRENT','Lucky Stop counter'),(800,after,'UPGRADE PREVIEW','Actual play • existing map lighting')]:
    draw.text((x+28,15),title,font=font,fill='#eeeeea');draw.text((x+28,51),detail,font=small,fill='#aeb8ba')
    sheet.paste(image.resize((800,600),Image.Resampling.LANCZOS),(x,92))
sheet.save(OUT/'in-game-comparison.png')
report=dict(preview_only=True,actual_play_verified=True,no_extra_lights=True,original_sources_unchanged=True,other_store_upgrades_preserved=True,physics_unchanged=True,editor_state_restored=True,geometry=checks)
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
