"""Check shipped geometry, UV atlas bounds, normals and resource dependency closure."""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'Assets'
REPORT = {}
for path in sorted((ASSETS/'attachments/hc1').glob('*/*.obj')):
    vertices, uvs, normals, faces = [], [], [], []
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            # Counter the explicit OBJ exporter swizzle to get engine coordinates.
            a,b,c=map(float,fields[1:]); vertices.append((c,a,b))
        elif fields[0] == 'vt':
            uvs.append(tuple(map(float,fields[1:])))
        elif fields[0] == 'vn':
            normals.append(tuple(map(float,fields[1:])))
        elif fields[0] == 'f':
            assert len(fields)==4, f'Non-triangle in {path}'
            faces.append([int(x.split('/')[0])-1 for x in fields[1:]])
    assert faces and len(faces)<15000
    assert len(vertices)==len(uvs)==len(normals)
    assert all(math.isfinite(x) for v in vertices+uvs+normals for x in v)
    assert all(abs(sum(x*x for x in n)-1)<0.005 for n in normals)
    assert all(0.019<=x<=0.981 and abs(x-0.5)>=0.019 for uv in uvs for x in uv)
    degenerate=0
    for ia,ib,ic in faces:
        a,b,c=vertices[ia],vertices[ib],vertices[ic]
        ab=[b[i]-a[i] for i in range(3)]; ac=[c[i]-a[i] for i in range(3)]
        cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        degenerate+=sum(x*x for x in cross)<1e-18
    assert degenerate==0, f'{path}: {degenerate} zero-area triangles'
    REPORT[path.stem]={'triangles':len(faces),'degenerate_triangles':degenerate,
                       'uv_gutter_fraction':0.02,
                       'bounds_min':[min(v[i] for v in vertices) for i in range(3)],
                       'bounds_max':[max(v[i] for v in vertices) for i in range(3)]}

for vmdl in (ASSETS/'attachments/hc1').glob('*/*.vmdl'):
    for dependency in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"',vmdl.read_text()):
        assert (ASSETS/dependency).is_file(),dependency

for part in (ASSETS/'gunsmith/hc1').glob('*/*.gnsmth'):
    resource=json.loads(part.read_text())
    prefab=ASSETS/resource['MainPrefab']
    assert prefab.is_file()
    data=json.loads(prefab.read_text())
    for component in data['RootObject']['Components']:
        if component['__type']=='Sandbox.ModelRenderer':
            assert (ASSETS/component['Model']).is_file()
    for equipment in resource['EligibleEquipment']:
        # Case-insensitive content lookup also works on case-sensitive build hosts.
        assert any(str(x.relative_to(ASSETS)).replace('\\','/').lower()==equipment
                   for x in (ASSETS/'Weapons').glob('*/*.equip')),equipment

out=ROOT/'Sources/Attachments/qa/validation.json'
out.write_text(json.dumps({'passed':True,'meshes':REPORT},indent=2)+'\n')
print(json.dumps({'passed':True,'models':len(REPORT),'triangles':{k:v['triangles'] for k,v in REPORT.items()}}))
