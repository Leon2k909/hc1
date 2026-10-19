from pathlib import Path
import hashlib
import json
import re

root=Path(__file__).resolve().parents[3]
folder=Path(__file__).resolve().parent
records=[]
for stage in ('finish-stage','hall-stage'):
    for source in sorted((folder/stage).rglob('*')):
        if not source.is_file(): continue
        relative=source.relative_to(folder/stage)
        target=root/'Assets'/relative
        if source.suffix=='.vmdl':
            old=target.read_text(encoding='utf-8')
            new=source.read_text(encoding='utf-8')
            marker='_class = "PhysicsShapeList"'
            if marker in old:
                assert old.split(marker,1)[1] == new.split(marker,1)[1], f'Physics differs: {relative}'
        if source.suffix=='.obj':
            counts=[0,0,0]
            triangles=0
            for line in source.read_text(encoding='utf-8').splitlines():
                if line.startswith('v '): counts[0]+=1
                elif line.startswith('vt '): counts[1]+=1
                elif line.startswith('vn '): counts[2]+=1
                elif line.startswith('f '):
                    triangles+=1
                    for value in line.split()[1:]:
                        for index,limit in zip(value.split('/'),counts):
                            assert not index or 0<int(index)<=limit,(relative,value,counts)
            print(relative,triangles,'triangles; valid indices')
        records.append({'path':relative.as_posix(),'source':source.relative_to(root).as_posix(),
                        'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                        'before_sha256':hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None})
(folder/'import.json').write_text(json.dumps({'files':records,'physics_unchanged':True},indent=2),encoding='utf-8')
print(len(records),'files verified; collision blocks unchanged')
