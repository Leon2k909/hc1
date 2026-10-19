from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).resolve().parent
stage = folder / 'ironwork-stage'
records = []
for source in sorted(stage.rglob('*')):
    if not source.is_file():
        continue
    relative = source.relative_to(stage)
    target = root / 'Assets' / relative
    if source.suffix == '.vmdl':
        new = source.read_text(encoding='utf-8')
        marker = '_class = "PhysicsShapeList"'
        if target.exists():
            old = target.read_text(encoding='utf-8')
            if marker in old:
                assert old.split(marker, 1)[1] == new.split(marker, 1)[1], relative
        else:
            assert source.stem == 'railhead_ironwork'
            assert 'PhysicsHullFile' not in new and 'PhysicsShapeBox' not in new
    if source.suffix == '.obj':
        counts = [0, 0, 0]
        triangles = 0
        for line in source.read_text(encoding='utf-8').splitlines():
            if line.startswith('v '): counts[0] += 1
            elif line.startswith('vt '): counts[1] += 1
            elif line.startswith('vn '): counts[2] += 1
            elif line.startswith('f '):
                triangles += 1
                assert len(line.split()) == 4
                for value in line.split()[1:]:
                    for index, limit in zip(value.split('/'), counts):
                        assert not index or 0 < int(index) <= limit, (relative, value, counts)
        print(relative, triangles, 'triangles; valid indices')
    records.append({
        'path': relative.as_posix(), 'source': source.relative_to(root).as_posix(),
        'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'before_sha256': hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
    })
(folder / 'ironwork-import.json').write_text(json.dumps({'files': records, 'physics_unchanged': True}, indent=2), encoding='utf-8')
calls = [{'name': 'asset_compile', 'arguments': {'path': record['path']}}
         for record in records if record['path'].endswith(('.vmat', '.vmdl'))]
(folder / 'ironwork-compile.json').write_text(json.dumps({'calls': calls}), encoding='utf-8')
exchange = Path(r'C:\Users\leon2\AppData\Local\Temp\sbox-cli\72171ce964804002b26c34a6d0c99adf')
script = (exchange / 'railhead-import.cs').read_text(encoding='utf-8')
script = script.replace('quality/import.json', 'quality/ironwork-import.json')
(exchange / 'railhead-ironwork-import.cs').write_text(script, encoding='utf-8')
print(len(records), 'files verified; collision unchanged')
