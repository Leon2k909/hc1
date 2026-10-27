"""Compare exported facade framing with the installed pre-change geometry."""
import hashlib
import json
from pathlib import Path

import forestbase_map as M
import forestbase_structures as S
from forestbase_cascade_width_audit import groups
from forestbase_sheds_audit import mesh

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/forestbase'
BEFORE=OUT/'facade-piers-before'
STAGE=OUT/'facade-piers-stage'
RES='models/maps/forestbase'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    hashes=json.loads((BEFORE/'model-hashes.json').read_text())
    modeldocs={name:sha(ROOT/'Assets'/RES/f'{name}.vmdl')==value
               for name,value in hashes.items()}
    assert all(modeldocs.values())
    assert sha(ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene')==sha(
        BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene')
    geometry={}
    for name in ('barracks','command'):
        old=BEFORE/'Assets'/RES/f'{name}.obj'
        new=STAGE/RES/f'{name}.obj'
        # Exact ModelDoc equality includes every serialized physics shape,
        # material remap and render-import setting, not merely shape counts.
        assert sha(STAGE/RES/f'{name}.vmdl')==hashes[name]
        a,b=groups(old),groups(new)
        assert a.keys()==b.keys()
        unchanged={p:a[p]==b[p] for p in a
                   if p not in ('structural_steel','case_hardware')}
        assert all(unchanged.values())
        geometry[name]=dict(before=mesh(old),after=mesh(new),
                            unchangedMaterialGeometry=unchanged)

    # Inspect the actual four exterior wall calls for both floors/buildings.
    # Check the widest frame plates, not just their center positions.
    walls=[];original=M.wall
    def capture(*args,**kwargs):
        wall=original(*args,**kwargs)
        if wall.outward:walls.append(wall)
        return wall
    M.wall=capture
    try:
        M.building('Barracks',(-950,850),(680,430),visual=False)
        M.building('Command',(265,920),(620,430),command=True,visual=False)
    finally:M.wall=original
    assert len(walls)==16
    counts=[];clearance=[]
    for wall in walls:
        piers=S.facade_piers(wall);counts.append(len(piers))
        for r in piers:
            assert wall.run[0]<=r-5<r+5<=wall.run[1]
            for hole in wall.openings:
                gap=max(hole.r0-(r+5),(r-5)-hole.r1)
                assert gap>=3-1e-8,'Frame plate overlaps an aperture'
                clearance.append(gap)
        assert all(hole.z1<=wall.z[1]-8 for hole in wall.openings)
    # Every wall's two floor calls have identical projected openings/piers.
    for start in (0,8):
        for side in range(4):
            assert S.facade_piers(walls[start+side])==S.facade_piers(walls[start+side+4])

    old_layout=json.loads((BEFORE/'output/forestbase/layout.json').read_text())
    new_layout=json.loads((STAGE/'layout.json').read_text())
    for name in ('barracks','command'):
        assert new_layout['stats'][name]['triangles']==geometry[name]['after']['triangles']
        new_layout['stats'][name]=old_layout['stats'][name]
    assert old_layout==new_layout
    report=dict(scope='Offline geometry and source preservation; no native rendering or performance acceptance.',
        allNineInstalledModelDocsUnchanged=modeldocs,candidateModelDocsIdentical=True,
        serializedCollisionAndMaterialRemapsUnchanged=True,sceneUnchanged=True,
        layoutUnchangedOutsideTwoTriangleCounts=True,geometry=geometry,
        exteriorWallFaces=16,fullHeightPiers=sum(counts),piersPerWall=counts,
        minimumPlateToApertureGapInches=min(clearance),floorsVerticallyAligned=True,
        newSceneObjects=0,newTextures=0,newShaders=0,
        sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (
            ROOT/'Tools/forestbase_map.py',ROOT/'Tools/forestbase_structures.py',
            ROOT/'Tools/forestbase_facade_piers_audit.py')},
        limitations=['Offline framing inspection does not establish native import, appearance, draw cost or FPS.',
            'Earlier hall, bridge and cargo collision changes still require fresh native acceptance.'])
    (STAGE/'geometry-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('geometry','sourceHashes','limitations')}))


if __name__=='__main__':main()
