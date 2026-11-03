from collections import Counter
import json, sys
import native
sys.path.insert(0,str(native.ROOT/'Tools'))
import riverdale_splice as S

for suffix in ('detail','fine'):
    name=f'riverdale_hall_{suffix}'
    candidate=Counter(S.read_obj(native.OUT/'stage'/f'{name}.obj')[1])
    old=Counter(S.read_obj(native.OUT/'stage'/f'{name}-old.obj')[1])
    p=native.OUT/'stage'/f'{name}-new.obj'
    new=Counter(S.read_obj(p)[1]) if p.exists() else Counter()
    baseline=candidate-new+old
    current=Counter(S.read_obj(native.ROOT/'Assets/models/maps/riverdale'/f'{name}.obj')[1])
    added=current-baseline; removed=baseline-current
    def mats(counter):
        result=Counter()
        for (material,_),n in counter.items():result[material]+=n
        return dict(result)
    print(json.dumps(dict(model=name,added=mats(added),removed=mats(removed),missing_camera_faces=sum((old-current).values()))))
