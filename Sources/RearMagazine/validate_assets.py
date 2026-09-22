"""Validate authored mesh data and the weapon-specific attachment asset graph."""
from pathlib import Path
import json
import math
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'Assets'
ART = ASSETS / 'attachments/rear_mag'
report = {}
for path in sorted(ART.glob('*/*.obj')):
    if path.parent.name == 'legacy':
        continue
    vertices, normals, uvs, faces = [], [], [], []
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        target = {'v': vertices, 'vn': normals, 'vt': uvs}.get(fields[0])
        if target is not None:
            values = tuple(map(float, fields[1:]))
            assert all(map(math.isfinite, values)), path
            target.append(values)
        elif fields[0] == 'f':
            faces.append([tuple(map(int, vertex.split('/'))) for vertex in fields[1:]])
    assert faces and all(len(face) == 3 for face in faces), path
    assert all(0 <= x <= 1 for uv in uvs for x in uv), path
    assert all(abs(sum(x*x for x in n) - 1) < .001 for n in normals), path
    for face in faces:
        assert all(1 <= v <= len(vertices) and 1 <= t <= len(uvs) and 1 <= n <= len(normals) for v, t, n in face), path
        a, b, c = [vertices[v-1] for v, _, _ in face]
        u, v = [tuple(q-p for p, q in zip(a, b)), tuple(q-p for p, q in zip(a, c))]
        cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
        assert sum(x*x for x in cross) > 1e-16, path
    model = path.with_suffix('.vmdl').read_text()
    for reference in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"', model):
        assert (ASSETS / reference).is_file(), reference
    report[path.parent.name] = len(faces)
assert len(report) == 12, report
for weapon in ('m4a1', 'scarh'):
    parts = list((ASSETS / 'gunsmith' / weapon / 'rear_mag').glob('*.gnsmth'))
    assert len(parts) == 4
    for path in parts:
        part = json.loads(path.read_text())
        assert part['Category'] in (14, 15) and part['RequiredLevel'] == 0
        assert part['EligibleEquipment'] == [f'weapons/{weapon}/{weapon}.equip']
        prefab = json.loads((ASSETS / part['MainPrefab']['prefab']).read_text())
        components = prefab['RootObject']['Components']
        renderer = next(c for c in components if c['__type'] == 'Sandbox.ModelRenderer')
        assert (ASSETS / renderer['Model']).is_file()
        mount = next(c for c in components if c['__type'].endswith('GunsmithBoneAttachment'))
        for variant in mount['ModelVariants'].values():
            assert (ASSETS / variant).is_file()
        if part['Category'] == 15:
            assert mount['HiddenBodygroup'] == 'magazine'
            assert (part['MagazineCapacity'], part['ReloadTimeMultiplier']) in ((20, .9), (40, 1.15))
atlas = ART / 'textures/rear_mag_atlas_color.png'
dimensions = struct.unpack('>II', atlas.read_bytes()[16:24])
assert dimensions[0] == dimensions[1] and dimensions[0] >= 1024
result = {'result': 'PASS', 'mesh_triangles': report, 'parts': 8, 'atlas': dimensions}
(ROOT / 'Sources/RearMagazine/qa/asset-validation.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
