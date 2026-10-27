"""Check that narrowing changes only cascade geometry, not other map content."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/forestbase'
BEFORE=OUT/'cascade-width-before';STAGE=OUT/'cascade-width-stage'
RES='models/maps/forestbase'
ALLOWED={'cascade_rock','waterfall_0','waterfall_1','waterfall_2','waterfall_3','waterfall_spray','waterfall_impact'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def groups(path):
    vertices=[];uv=[];normals=[];parts={};paint=None
    for line in path.read_text().splitlines():
        fields=line.split()
        if not fields:continue
        if fields[0]=='v':vertices.append(tuple(fields[1:]))
        elif fields[0]=='vt':uv.append(tuple(fields[1:]))
        elif fields[0]=='vn':normals.append(tuple(fields[1:]))
        elif fields[0]=='usemtl':paint=fields[1];parts[paint]=hashlib.sha256()
        elif fields[0]=='f':
            values=[]
            for field in fields[1:]:
                v,t,n=(int(x)-1 for x in field.split('/'))
                values.append((vertices[v],uv[t],normals[n]))
            parts[paint].update(repr(values).encode())
    return {key:value.hexdigest() for key,value in parts.items()}


def main():
    a=groups(BEFORE/'Assets'/RES/'vista.obj');b=groups(STAGE/RES/'vista.obj')
    assert a.keys()==b.keys()
    unchanged={key:a[key]==b[key] for key in a if key not in ALLOWED}
    assert all(unchanged.values()), 'Unrelated geometry/UV/normal data changed'
    changed=[key for key in a if a[key]!=b[key]]
    assert set(changed)<=ALLOWED
    models=json.loads((BEFORE/'model-hashes.json').read_text())
    preserved={n:sha(ROOT/'Assets'/RES/f'{n}.vmdl')==h for n,h in models.items()}
    assert all(preserved.values())
    assert sha(ROOT/'Assets/scenes/maps/ForestBase/forestbase.scene')==sha(BEFORE/'Assets/scenes/maps/ForestBase/forestbase.scene')
    assert sha(STAGE/RES/'vista.vmdl')==sha(BEFORE/'Assets'/RES/'vista.vmdl')
    report=json.loads((STAGE/RES/'geometry-audit.json').read_text())
    assert report['overallWidthRange']==[640.,780.]
    assert not report['occludedByNewOrRefittedRock'] and max(report['sharedEdgeMaximumErrors'])<.002
    old=json.loads((BEFORE/'output/forestbase/layout.json').read_text())
    new=json.loads((STAGE/'layout.json').read_text());assert old==new
    evidence=dict(scope='Offline exported cascade and unrelated geometry preservation. No native shader, collision, animation or FPS verification.',
                  allNineMainModelDocsUnchanged=preserved,sceneUnchanged=True,layoutUnchanged=True,
                  unchangedMaterialGeometry=unchanged,changedMaterialGeometry=changed,
                  crownWidthMetresBefore=1315*.0254,crownWidthMetresAfter=780*.0254,footWidthMetres=640*.0254,
                  cascadeGeometryAudit=report,
                  sourceHashes={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Tools/forestbase_cascade.py',ROOT/'Tools/forestbase_cascade_audit.py',ROOT/'Tools/forestbase_cascade_width_audit.py')})
    (STAGE/'preservation-audit.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('cascadeGeometryAudit','sourceHashes')}))


if __name__=='__main__':main()
