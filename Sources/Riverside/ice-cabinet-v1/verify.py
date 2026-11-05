"""Verify candidate geometry and compose unedited native captures for review."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[3]
output=root/'output/riverside/ice-cabinet-v1'
manifest=json.loads((output/'manifest.json').read_text())
native=json.loads((output/'isolated-native-review.json').read_text())
assert native['UserStatePreserved']
models=root/'Assets/models/maps/riverside/ice-cabinet-v1'
report=[]
for lod,expected in enumerate(manifest['triangles']):
    vertices=[];normals=[];uvs=[];faces=[]
    for line in (models/f'ice_cabinet_lod{lod}.obj').read_text().splitlines():
        if line.startswith('v '):vertices.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):normals.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uvs.append(list(map(float,line.split()[1:])))
        elif line.startswith('f '):faces.append([list(map(int,t.split('/'))) for t in line.split()[1:]])
    v=np.asarray(vertices);n=np.asarray(normals)
    assert np.isfinite(v).all() and np.isfinite(n).all() and np.isfinite(uvs).all()
    # map_kit writes normals to three decimal places (maximum rounding error sqrt(3)*.0005).
    normal_error=float(np.max(abs(np.linalg.norm(n,axis=1)-1)))
    assert normal_error<.00087
    areas=[]
    for face in faces:
        assert len(face)==3
        for vi,ti,ni in face:assert 1<=vi<=len(v) and 1<=ti<=len(uvs) and 1<=ni<=len(n)
        a,b,c=v[[p[0]-1 for p in face]]
        areas.append(float(np.linalg.norm(np.cross(b-a,c-a))*.5))
    assert min(areas)>1e-8 and len(faces)==expected
    assert native['Models'][1]['Mesh']['Meshes'][lod]['Triangles']==expected
    report.append(dict(lod=lod,triangles=len(faces),min_triangle_area=min(areas),finite=True,indices_valid=True,max_normal_length_error=normal_error))
vmdl=(models/'ice_cabinet.vmdl').read_text()
assert 'dimensions = [ 38.0000, 30.0000, 60.0000 ]' in vmdl
project=Path('C:/sbox-projects/hc1/forked-shooter-main')
source_checks={k:hashlib.sha256((project/manifest[k]).read_bytes()).hexdigest()==manifest[h] for k,h in [('source_model','source_sha256'),('source_vmdl','source_vmdl_sha256')]}
assert all(source_checks.values())
for relative,digest in manifest['files'].items():
    assert hashlib.sha256((project/relative).read_bytes()).hexdigest()==digest,relative
comparison=Image.new('RGB',(1600,880),'#111416')
draw=ImageDraw.Draw(comparison)
font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',28)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for x,name,label,detail in [(0,'before','CURRENT','Flat cabinet and painted door'),(800,'after','UPGRADE PREVIEW','Modeled fittings, vents and worn enamel')]:
    draw.text((x+30,18),label,font=font,fill='#eeeeea')
    draw.text((x+30,56),detail,font=small,fill='#aeb8ba')
    comparison.paste(Image.open(output/f'isolated-{name}.png').resize((800,800),Image.Resampling.LANCZOS),(x,80))
comparison.save(output/'comparison.png')
result=dict(mesh_checks=report,collision_dimensions=[38,30,60],source_unchanged=source_checks,native_resources_match=True,user_state_preserved=native['UserStatePreserved'],preview_only=True)
(output/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
