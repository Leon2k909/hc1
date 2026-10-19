from pathlib import Path
from collections import Counter
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import lowtide_container as C
import lowtide_map as LT
OUT=Path(__file__).resolve().parent/'container-detail'

def faces(text):
    positions=[]
    material=None
    result=Counter()
    for line in text.splitlines():
        fields=line.split()
        if not fields: continue
        if fields[0]=='v': positions.append(tuple(float(x) for x in fields[1:]))
        elif fields[0]=='usemtl': material=fields[1]
        elif fields[0]=='f':
            key=(material,tuple(positions[int(x.split('/')[0])-1] for x in fields[1:]))
            result[key]+=1
    return result

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    backup=OUT/'before'
    backup.mkdir(exist_ok=True)
    old_script=backup/'lowtide_container.py'
    if not old_script.exists(): shutil.copyfile(ROOT/'Tools/lowtide_container.py',old_script)
    report={}
    for name,records in C.layouts().items():
        model=K.Model()
        for args,kwargs in records: C.build(model,*args,**kwargs)
        LT.configure(model)
        generated=OUT/(name+'-old.obj')
        K.write_obj(generated,model,name)
        path=ROOT/'Assets/models/maps/lowtide'/f'{name}.obj'
        actual=faces(path.read_text())
        expected=faces(generated.read_text())
        missing=expected-actual
        assert not missing, (name,sum(missing.values()),list(missing)[:1])
        for suffix in ('.obj','.mtl','.vmdl'):
            p=path.with_suffix(suffix)
            target=backup/p.name
            if target.exists(): assert target.read_bytes()==p.read_bytes(), p
            else: shutil.copyfile(p,target)
        report[name]={'old_container_triangles':sum(expected.values()),'all_triangles':sum(actual.values()),'old_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    protected={}
    for directory in ('Assets/models/maps/lowtide','Assets/materials/lowtide','Assets/scenes/maps/Lowtide'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and not p.name.endswith('_c') and p.suffix not in ('.obj',):
                protected[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
            elif p.is_file() and p.suffix=='.obj' and p.name not in ('lowtide_dress_east.obj','lowtide_dress_west.obj'):
                protected[p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT/'before.json').write_text(json.dumps({'models':report,'protected':protected},indent=2)+'\n')
    print(json.dumps({'models':report,'protected':len(protected)},indent=2))
