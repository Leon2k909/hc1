from pathlib import Path
from collections import Counter
import sys
sys.path.insert(0,'Tools')
from riverdale_splice import read_obj
root=Path('output/riverdale/radiation-monitor-v2')
def counts(faces):
    result=Counter()
    for (material,corners),n in faces.items():
        result[material]+=n
    return result
for name in ('riverdale_hall_detail','riverdale_hall_fine'):
    a=Counter(read_obj(root/('stage/models/maps/riverdale/'+name+'.obj'))[1])
    b=Counter(read_obj(Path('Assets/models/maps/riverdale')/(name+'.obj'))[1])
    removed,added=a-b,b-a
    print(name,'Removed',counts(removed),'Added',counts(added))
    print('Sample removed',list(removed.items())[:1])
    print('Sample added',list(added.items())[:1])
