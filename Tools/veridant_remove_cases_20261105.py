"""Remove map-only case imports and exact collision boxes; retain reusable assets."""
from pathlib import Path
import json, re, shutil, hashlib
from collections import Counter
import numpy as np
import map_kit as K
from veridant_case_placements import placements
from belltower_safe_imports import span, sha

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/remove-cases-20261105'

def key(node):
    def v(name):
        return tuple(round(float(x),4) for x in re.search(name+r'\s*=\s*\[([^]]+)\]',node)[1].split(','))
    return (v('origin'),v('angles'),v('dimensions'),re.search(r'surface_prop\s*=\s*"([^"]+)"',node)[1])

def main():
    assert not OUT.exists(), 'Preserve existing evidence'
    OUT.mkdir(parents=True)
    rows=placements()
    assert len(rows)==82 and rows==json.loads((ROOT/'output/veridant/cases-v3/placements.json').read_text())
    (OUT/'placements-before.json').write_text(json.dumps(rows,indent=2))
    protected={}
    for folder in ('Assets/models/maps/veridant/cases-v4','Assets/materials/veridant/cases-v4'):
        for p in (ROOT/folder).rglob('*'):
            if p.is_file(): protected[p.relative_to(ROOT).as_posix()]=sha(p)
    for p in ('Assets/scenes/maps/Veridant/veridant.scene','Tools/veridant_parts.py','Tools/veridant_transport_case.py','Tools/veridant_case_detail.py'):
        protected[p]=sha(ROOT/p)
    files={}; reports={}
    for name in ('veridant_buildings','veridant_dress'):
        path=f'Assets/models/maps/veridant/{name}.vmdl'
        raw=(ROOT/path).read_text(); ranges=[]
        imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',raw)
        removed=[p for p in imports if '/cases-v4/' in p]
        assert removed and not any('/cases-v3/' in p for p in imports)
        for p in imports:
            protected['Assets/'+p]=sha(ROOT/'Assets'/p)
        protected[f'Assets/models/maps/veridant/{name}.obj']=sha(ROOT/f'Assets/models/maps/veridant/{name}.obj')
        for p in removed:ranges.append(span(raw,f'filename = "{p}"'))
        expected=Counter()
        for r in rows:
            if r['model']!=name:continue
            f=np.array((*r['along'],0.)); f/=np.linalg.norm(f)
            axes=[K.to_world(x) for x in (f,np.cross((0,0,1),f),np.array((0,0,1))) ]
            centre=np.array((*r['centre'],r['z0']))+np.array((0,0,r['size'][2]/2))
            expected[(tuple(round(float(x),4) for x in K.to_world(centre)),tuple(round(float(x),4) for x in K.angles_of(axes)),tuple(r['size']),r['surface'])]+=1
        matched=Counter(); retained=[]
        for m in re.finditer(r'_class\s*=\s*"PhysicsShapeBox"',raw):
            # span() finds the first marker, so use a unique suffix beginning at this node.
            a=raw.rfind('{',0,m.start()); depth=0; b=None
            for i in range(a,len(raw)):
                if raw[i]=='{':depth+=1
                elif raw[i]=='}':
                    depth-=1
                    if depth==0:b=i+1;break
            node=raw[a:b]; k=key(node)
            if matched[k]<expected[k]: ranges.append((a,b));matched[k]+=1
            else:retained.append(node)
        assert matched==expected,(name,expected-matched)
        updated=raw
        for a,b in sorted(ranges,reverse=True):
            end=b
            while end<len(updated) and updated[end].isspace():end+=1
            if end<len(updated) and updated[end]==',':end+=1
            updated=updated[:a]+updated[end:]
        assert all(node in updated for node in retained)
        assert [p for p in imports if p not in removed]==re.findall(r'filename\s*=\s*"([^"]+\.obj)"',updated)
        before=OUT/'before'/path;before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/path,before)
        target=OUT/'staged'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(updated)
        files[path]={'before':sha(ROOT/path),'after':sha(target),'source':str(target)}
        reports[name]={'cases_removed':sum(expected.values()),'render_imports_removed':removed,'remaining_collision_boxes':len(retained)}
    layout=ROOT/'Tools/veridant_map.py';raw=layout.read_text();shutil.copy2(layout,OUT/'veridant_map-before.py')
    updated=raw.replace('P.case_stack(', '_omit_transport_cases(').replace('P.hard_case(', '_omit_transport_cases(')
    assert updated!=raw
    # Preserve argument evaluation, including seeded layout RNG consumption.
    updated+='\n\ndef _omit_transport_cases(*args, **kwargs):\n    """Transport cases are intentionally absent from Veridant; assets remain reusable."""\n    return None\n'
    # Define before the executable main guard, for command-line regeneration too.
    helper=updated[updated.rfind('\n\ndef _omit_transport_cases'):];updated=updated[:updated.rfind('\n\ndef _omit_transport_cases')]
    index=updated.index('\nif __name__')
    updated=updated[:index]+helper+'\n'+updated[index:]
    layout.write_text(updated)
    import veridant_map as V
    import importlib
    importlib.reload(V)
    assert placements()==[]
    manifest={'files':files,'models':reports,'protected':protected,'cases_removed':len(rows),'layout_before':hashlib.sha256(raw.encode()).hexdigest(),'layout_after':sha(layout)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'cases':len(rows),'models':reports,'protected_files':len(protected)}))

if __name__=='__main__':main()
