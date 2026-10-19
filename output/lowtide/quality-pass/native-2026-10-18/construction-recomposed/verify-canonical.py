from pathlib import Path
import importlib.util
import json
import sys
from collections import Counter

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
BASE=ROOT/'output/lowtide/quality-pass'
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import lowtide_map as L
import lowtide_finish as F
import lowtide_construction as C
import lowtide_window_construction as W

spec=importlib.util.spec_from_file_location('lowtide_before_construction',OUT/'generator-before/lowtide_map.py')
old=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=old
spec.loader.exec_module(old)
target=OUT/'canonical-verification'
target.mkdir(exist_ok=True)
def keys(model,name,asset_name=None):
    L.configure(model)
    path=target/(name+'.obj')
    K.write_obj(path,model,asset_name or name)
    return W.face_keys(path.read_text(),attributes=True)

report={}
layout=json.loads((BASE/'window-construction/layout.json').read_text())['models']
for name,rows in layout.items():
    before,after=K.Model(),K.Model()
    old_glass,new_glass=K.Model(),K.Model()
    for row in rows:
        wall,opening,style=W.unpack(row,L)
        old.window(before,wall,opening,style,glass=old_glass if row['transparent'] else None)
        L.window(after,wall,opening,style,glass=new_glass if row['transparent'] else None)
    a,b=keys(before,name+'-before-windows',name),keys(after,name+'-after-windows',name)
    minus=W.face_keys((BASE/'window-construction'/f'{name}-old.obj').read_text(),attributes=True)
    plus=W.face_keys((BASE/'window-construction'/f'{name}-new.obj').read_text(),attributes=True)
    assert b==a-minus+plus, f'Canonical window mismatch: {name}'
    assert keys(old_glass,name+'-before-glass',name)==keys(new_glass,name+'-after-glass',name)
    assert repr(old_glass.boxes)==repr(new_glass.boxes)
    report[name+'_windows']=dict(windows=len(rows),exact_corner_attributes=True,glass_and_collision_preserved=True)
    print(f'Canonical {name}: {len(rows)} windows and glass match',flush=True)

doors=json.loads((BASE/'door-construction/layout.json').read_text())['models']
for name,rows in doors.items():
    before,after=K.Model(),K.Model()
    selected=0
    for row in rows:
        wall,opening,style=W.unpack(row,L)
        old.leaves_shut(before,wall,opening,style)
        L.leaves_shut(after,wall,opening,style)
        selected+=C.is_shed_door(L,wall,opening)
    a,b=keys(before,name+'-before-doors',name),keys(after,name+'-after-doors',name)
    expected=a
    if selected:
        minus=W.face_keys((BASE/'door-construction'/f'{name}-old.obj').read_text(),attributes=True)
        plus=W.face_keys((BASE/'door-construction'/f'{name}-new.obj').read_text(),attributes=True)
        expected=a-minus+plus
    assert b==expected,f'Canonical door or threshold mismatch: {name}'
    report[name+'_doors']=dict(available=len(rows),changed=selected,exact_corner_attributes=True,thresholds_preserved=True)
    print(f'Canonical {name}: {selected} shed door pairs and unchanged thresholds match',flush=True)

drains=K.Model()
for side in (-1,1):
    for kind,values in F.drainage_layout(L,side):
        (F.drainpipe if kind=='pipe' else F.gutter)(drains,L,*values)
assert keys(drains,'drainage','lowtide_finish')==W.face_keys((BASE/'drain-junctions/junctions-new.obj').read_text(),attributes=True)
report['drainage']=dict(exact_corner_attributes=True,triangles=drains.triangle_count())
print('Canonical pipes and pierced gutters match the reviewed junction geometry',flush=True)
for name,tint,metal,rough in [('lt_drain_iron','.48 .51 .48',.45,.62),('lt_drain_edge','.72 .74 .70',.6,.48)]:
    assert C.metal_material(tint,metal,rough)==(OUT/'stage/Assets/materials/lowtide/finish'/f'{name}.vmat').read_text()
report['materials_reproduced']=2
report['generator_sources']={str(Path(p).relative_to(ROOT)):W.sha(p) for p in (L.__file__,F.__file__,C.__file__)}
(OUT/'canonical-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
