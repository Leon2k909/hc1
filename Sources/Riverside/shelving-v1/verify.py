from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shelving-v1'
m=json.loads((OUT/'manifest.json').read_text());r=json.loads((OUT/'runtime-review.json').read_text());materials=json.loads((OUT/'materials-verified.json').read_text())
assert r['ActualPlayMode'] and r['PlayerCount']>0 and not r['ErrorModels'] and r['NoExtraLights']
assert json.loads((OUT/'state-restored.json').read_text())['restored']
assert materials['AllMaterialsLoaded'] and materials['NoEmission']
assert r['Candidate']['LodCount']==3 and [mesh['Triangles'] for mesh in r['Candidate']['Meshes']]==m['triangles']
assert [mesh['LodMask'] for mesh in r['Candidate']['Meshes']]==[1,2,4]
assert r['PublicStore']['TotalTriangles']-r['StoreWithout']['TotalTriangles']==96
a={mesh['Name']:mesh for mesh in r['PublicStore']['Meshes']};b={mesh['Name']:mesh for mesh in r['StoreWithout']['Meshes']}
for name,mesh in a.items():
    assert mesh['LodMask']==b[name]['LodMask']
    assert mesh['Triangles']-b[name]['Triangles']==(96 if name=='riverside_store' else 0)
checks=[]
for lod,expected in enumerate(m['triangles']):
    vertices=[];normals=[];uv=[];faces=[]
    for line in (REVIEW/f'Assets/models/maps/riverside/shelving-v1/gondola_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):vertices.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):normals.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uv.append(list(map(float,line.split()[1:])))
        elif line.startswith('f '):faces.append([list(map(int,p.split('/'))) for p in line.split()[1:]])
    v=np.asarray(vertices);n=np.asarray(normals)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uv).all()
    assert max(abs(np.linalg.norm(n,axis=1)-1))<.00087
    # OBJ is Y-up: length X, height Y, depth Z. A 90-degree instance yaw matches the old shelves.
    assert np.max(abs(v[:,0]))<=35.001 and v[:,1].min()>=0 and v[:,1].max()<=56.001 and np.max(abs(v[:,2]))<=18.001
    areas=[]
    for face in faces:
        assert len(face)==3
        for vi,ti,ni in face:assert 1<=vi<=len(v) and 1<=ti<=len(uv) and 1<=ni<=len(n)
        x,y,z=v[[p[0]-1 for p in face]];areas.append(float(np.linalg.norm(np.cross(y-x,z-x))*.5))
    assert len(faces)==expected and min(areas)>1e-8
    checks.append(dict(lod=lod,triangles=len(faces),minimum_triangle_area=min(areas),finite=True,indices_valid=True))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert all(sha(ROOT/p)==h for p,h in m['files'].items())
original=(ROOT/m['source_vmdl']).read_text();preview=(REVIEW/'Assets/models/maps/riverside/shelving-v1/store_without_shelving.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert original[original.index(marker):]==preview[preview.index(marker):]
before=Image.open(OUT/'in-game-before.png').convert('RGB');after=Image.open(OUT/'in-game-after.png').convert('RGB')
assert np.mean(abs(np.asarray(before,dtype=float)-np.asarray(after,dtype=float)))>10
sheet=Image.new('RGB',(1600,692),'#111416');draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
for offset,image,title,detail in [(0,before,'CURRENT','Flat luminous product panels'),(800,after,'UPGRADE PREVIEW','Actual play | existing map lighting')]:
    draw.text((offset+28,15),title,font=font,fill='#eeeeea');draw.text((offset+28,51),detail,font=small,fill='#aeb8ba')
    sheet.paste(image.resize((800,600),Image.Resampling.LANCZOS),(offset,92))
sheet.save(OUT/'in-game-comparison.png')
report=dict(preview_only=True,actual_play_verified=True,units=4,old_triangles_removed=96,no_emission=True,no_extra_lights=True,all_materials_loaded=True,physics_unchanged=True,other_upgrades_preserved=True,source_hashes_unchanged=True,editor_state_restored=True,geometry=checks)
(OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
