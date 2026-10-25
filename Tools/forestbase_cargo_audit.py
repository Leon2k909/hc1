"""Serialized collision preservation and source-grid checks for loading islands."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re

import forestbase_map as M
import forestbase_cargo as C
import forestbase_structure_audit as A
from forestbase_sheds_audit import hull_elements,mesh

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/forestbase'
BEFORE=OUT/'cargo-before';STAGE=OUT/'cargo-stage';RES='models/maps/forestbase'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def boxes(path):return re.findall(r'_class = "PhysicsShapeBox"[^}]+}',path.read_text())


def walk(nodes):
    for n in nodes:
        yield n
        yield from walk(n.get('Children',[]))


def main():
    old=json.loads((BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene').read_text())
    new=json.loads((STAGE/'forestbase.scene').read_text());restored=json.loads(json.dumps(new))
    a=list(walk(old['GameObjects']));b=list(walk(restored['GameObjects']));assert len(a)==len(b)==752
    moved=[]
    for before,after in zip(a,b):
        if before.get('Name') in ('DM 5','DM 12'):
            i=int(before['Name'].split()[1])-1
            pose=M.spawn(before['Name'],f'spawn/dm/{i}',M.DM[i],'Unassigned','deathmatch')
            assert after['Position']==pose['Position'] and after['Rotation']==pose['Rotation']
            moved.append(dict(name=before['Name'],before=before['Position'],after=after['Position'],
                              twoInchLiftPreserved=True,facingRegenerated=True))
            after['Position']=before['Position'];after['Rotation']=before['Rotation']
    assert restored==old and len(moved)==2
    models=M.build(visual_chunks=[]);parity={};changes={}
    expected=STAGE/'expected-physics';expected.mkdir(exist_ok=True)
    baseline=json.loads((BEFORE/'model-hashes.json').read_text())
    for name,m in models.items():
        M.K.write_vmdl(expected/f'{name}.vmdl',RES,name,m)
        actual=STAGE/RES/f'{name}.vmdl' if name in ('yard','logistics') else ROOT/'Assets'/RES/f'{name}.vmdl'
        parity[name]=boxes(actual)==boxes(expected/f'{name}.vmdl')
        assert parity[name], 'Source-grid boxes differ from serialized collision'
        grouped=defaultdict(list)
        for points,surface in m.hulls:grouped[surface].append(points)
        for surface,points in grouped.items():
            path=expected/f'{name}_hulls_{surface}.obj';M.K.write_hulls_obj(path,points)
            native=actual.parent/path.name
            assert hull_elements(path)==hull_elements(native), 'Source-grid hulls differ from serialized collision'
        if name not in ('yard','logistics'):
            assert sha(actual)==baseline[name]
            continue
        original=BEFORE/'Assets'/RES/f'{name}.vmdl';before_boxes=boxes(original);after_boxes=boxes(actual)
        assert after_boxes[:len(before_boxes)]==before_boxes
        assert len(after_boxes)-len(before_boxes)==(16 if name=='yard' else 24)
        for path in (BEFORE/'Assets'/RES).glob(name+'_hulls_*.obj'):
            assert sha(actual.parent/path.name)==sha(path)
        changes[name]=dict(boxesBefore=len(before_boxes),boxesAfter=len(after_boxes),
                           oldBoxesAndHullFilesPreserved=True,mesh=mesh(actual.with_suffix('.obj')))
    route=json.loads((STAGE/'routes/route-audit.json').read_text())
    assert route['radius']==24 and route['height']==72 and route['step']==18 and not route['problems']
    assert all(r['reachable'] for r in route['checks'])
    layout=json.loads((STAGE/'layout.json').read_text());before_layout=json.loads((BEFORE/'output/forestbase/layout.json').read_text())
    layout['dm']=before_layout['dm']
    for name in ('yard','logistics'):layout['stats'][name]=before_layout['stats'][name]
    assert layout==before_layout
    report=dict(scope='Offline serialized collision parity and conservative 8-inch source-grid reachability. No native controller, navmesh, bullet, roof-perch or multiplayer performance acceptance.',
                existingSceneObjectsPreserved=752,newSceneObjects=0,movedFfaSpawns=moved,
                sceneUnchangedOutsideTwoFfaPoses=True,serializedCollisionParity=parity,geometry=changes,
                loadingIslands=len(C.ISLANDS),cases=sum(rows*cols*tiers for chunk,name,p,rows,cols,tiers,angle in C.ISLANDS),
                palletProxies=6,serviceCanProxies=4,newBoxColliders=40,
                routeChecks=len(route['checks']),routeProblems=[],grid=route['grid'],radius=24,height=72,step=18,
                baselineProblems=json.loads((BEFORE/'routes/route-audit.json').read_text())['problems'],
                sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_map.py',ROOT/'Tools/forestbase_cargo.py',
                    ROOT/'Tools/forestbase_validate.py',ROOT/'Tools/forestbase_cargo_audit.py')},
                limitations=['New cargo changes gameplay collision and potential climbing/perches. Native movement, jumps, sightlines, navigation and balance must be checked again.',
                    'Radius 24 is a conservative audit clearance, not a claim about the live controller radius.',
                    'Old east-room probes were near expanded shelf bounds; replacement standing points are inside the same rooms between the partition and shelves.',
                    'Two FFA spawn positions move to free floor areas. Team spawns and objectives are unchanged.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('geometry','baselineProblems','sourceHashes','limitations')}))


if __name__=='__main__':main()
