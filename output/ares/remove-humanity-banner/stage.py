"""Remove only the two HUMANITY FURTHER assemblies from the installed mesh."""
import sys
import json
import hashlib
import shutil
from collections import Counter
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import ares_map as A
import map_kit as K
from railhead_stage_extinguisher import lookup_polygons,coverage,sha,point
from belltower_safe_imports import span

OUT=Path(__file__).resolve().parent
source=ROOT/'Assets/models/maps/ares/ares_dressing.obj'
target=OUT/'ares_dressing.obj'
assert not target.exists(),'Keep previous staging evidence.'
doc=ROOT/'Assets/models/maps/ares/ares_dressing.vmdl'
text=doc.read_text();a,b=span(text,'_class = "RenderMeshList"')
imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text[a:b])
assert imports==['models/maps/ares/ares_dressing.obj'],imports
old=K.Model()
specs=[((-150.,620.,690.),(0,-1),80.,240.),
       ((-A.HALL_E+60.,120.,690.),(1,0),90.,270.)]
for centre,facing,width,height in specs:
    A.banner(old,'banner_humanity',centre,facing,width,height)
assert not old.boxes and not old.hulls and old.triangle_count()==56
lookup,polygons=lookup_polygons(old)
before=sha(source);raw=source.read_bytes();lines=raw.splitlines(keepends=True)
vertices=[None];paint=None;found=Counter();removed=[];kept=[]
for index,line in enumerate(lines):
    if line.startswith(b'v '):vertices.append(point(line[2:].decode()))
    elif line.startswith(b'usemtl '):paint=line.split()[1]
    elif line.startswith(b'f '):
        pts=[vertices[int(t.split(b'/')[0])] for t in line.split()[1:]]
        key=(paint,frozenset(pts))
        if key in lookup:
            found[key]+=1;removed.append(index);continue
    kept.append(line)
coverage(found,lookup,polygons)
assert len(removed)==56
assert sha(source)==before,'The dressing was edited while staging.'
target.write_bytes(b''.join(kept))
backup=OUT/'before-ares_dressing.obj';shutil.copy2(source,backup);assert sha(backup)==before
assert raw==b''.join(lines)
assert target.read_bytes()==b''.join(l for i,l in enumerate(lines) if i not in set(removed))
# The Habitat B cloth, backing and hanging bars must all still be present.
habitat=K.Model();A.banner(habitat,'banner_habitat',(900.,640.,690.),(0,-1),90.,270.)
hlookup,hpolygons=lookup_polygons(habitat);hfound=Counter();paint=None
for line in kept:
    if line.startswith(b'usemtl '):paint=line.split()[1]
    elif line.startswith(b'f '):
        key=(paint,frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
        if key in hlookup:hfound[key]+=1
coverage(hfound,hlookup,hpolygons)
assert not re.search(r'banner\(\s*m,\s*[\'"]banner_humanity[\'"]', (ROOT/'Tools/ares_map.py').read_text())
protected={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in
    (doc,source.with_suffix('.mtl'),ROOT/'Assets/scenes/maps/Ares/ares.scene')}
manifest={'target':'Assets/models/maps/ares/ares_dressing.obj','before':before,'after':sha(target),
          'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix(),
          'banners_removed':2,'triangles_removed':56,'habitat_banner_preserved':True,
          'all_other_obj_bytes_and_indices_exact':True,'protected_sha256':protected}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
