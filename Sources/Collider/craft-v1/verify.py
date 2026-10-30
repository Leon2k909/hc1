"""Verify exported geometry and current installed resources independently."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

ROOT=Path(__file__).resolve().parents[3]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def read_obj(path):
    v=[];uv=[];n=[];f=[];paint=None;added=False;retained=[]
    for line in path.read_text().splitlines():
        if line.startswith('# Collider craft-v1:'):added=True
        if line.startswith('v '):v.append(list(map(float,line.split()[1:])))
        elif line.startswith('vt '):uv.append(list(map(float,line.split()[1:])))
        elif line.startswith('vn '):n.append(list(map(float,line.split()[1:])))
        elif line.startswith('usemtl '):paint=line.split()[1]
        elif line.startswith('f '):
            f.append((paint,[list(map(int,x.split('/'))) for x in line.split()[1:]],added))
            if not added:retained.append(line)
    return np.array(v),np.array(uv),np.array(n),f,retained


def check(stage,installed=False,baseline=None):
    manifest=json.loads((stage/'manifest.json').read_text());reports={}
    for name,expected in manifest['geometry'].items():
        rel=Path('models/maps/collider')/(name+'.obj')
        original=read_obj((baseline or stage/'before')/rel)
        candidate=read_obj(stage/'assets'/rel)
        for before,after in zip(original[:3],candidate[:3]):
            assert np.isfinite(after).all()
            assert np.array_equal(before,after[:len(before)]),'Original attribute table changed'
        v,uv,n,faces,retained=candidate
        assert len(faces)==expected['final_triangles']
        it=iter(original[4]);assert all(any(old==line for old in it) for line in retained),'Retained faces reordered/changed'
        minimum=float('inf');wrong=0;added=0
        for paint,indices,new in faces:
            assert len(indices)==3
            for vi,ti,ni in indices:assert 1<=vi<=len(v) and 1<=ti<=len(uv) and 1<=ni<=len(n)
            if not new:continue
            p=v[[row[0]-1 for row in indices]]
            cross=np.cross(p[1]-p[0],p[2]-p[0]);area=float(np.linalg.norm(cross)/2)
            assert area>1e-9,(paint,indices,'Degenerate exported triangle')
            minimum=min(minimum,area);added+=1
            average=np.mean(n[[row[2]-1 for row in indices]],axis=0)
            wrong+=np.dot(cross,average)<-1e-8
        assert wrong==0,(name,wrong)
        assert added==expected['added_triangles']
        before=((baseline or stage/'before')/rel.with_suffix('.vmdl')).read_bytes()
        after=(stage/'assets'/rel.with_suffix('.vmdl')).read_bytes()
        marker=b'\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
        if marker in before:assert before[before.index(marker):]==after[after.index(marker):]
        else:assert marker not in after
        reports[name]=dict(triangles=len(faces),added_triangles=added,minimum_added_area=minimum,
            winding_errors=int(wrong),original_attributes_preserved=True,retained_faces_preserved=True,physics_preserved=True)
    for entry in manifest['files']:
        assert sha(stage/'assets'/entry['relative'])==entry['after']
        if installed:assert sha(ROOT/'Assets'/entry['relative'])==entry['after']
    for p,value in manifest['protected'].items():assert sha(ROOT/'Assets'/p)==value,p
    for p,value in manifest['sources'].items():assert sha(ROOT/p)==value,p
    result=dict(success=True,installed=installed,files_verified=len(manifest['files']),models=reports)
    (stage/('installed-validation.json' if installed else 'source-validation.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--baseline',type=Path,default=ROOT/'output/collider-detail-v3-20261027/stage-v2/before')
    p.add_argument('--installed',action='store_true');a=p.parse_args()
    check(ROOT/a.stage if not a.stage.is_absolute() else a.stage,a.installed,
        ROOT/a.baseline if a.baseline and not a.baseline.is_absolute() else a.baseline)
