"""Append welded pipe heads to the installed hall without rebuilding its other meshes."""
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
from collections import Counter
import numpy as np
import ares_map as A
import ares_pipework as D
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/ares/pipe-end-fix'
TARGET='Assets/models/maps/ares/pressure-doors-v2/hall_base.obj'
MARKER=b'# ares-pipe-end-caps-v1\n'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def point(p):return tuple(round(float(x)*1000) for x in p)


def cap_edges(model):
    edges=Counter()
    for rows in model.polygons.values():
        for pts,normal in rows:
            assert np.isfinite(pts).all() and np.isfinite(normal).all()
            points=[point(K.obj_vector(K.to_world(p)).split()) for p in pts]
            for i in range(1,len(points)-1):
                triangle=[points[0],points[i],points[i+1]]
                assert len(set(triangle))==3
                for j in range(3):edges[frozenset((triangle[j],triangle[(j+1)%3]))]+=1
    assert all(n in (1,2) for n in edges.values()),'Non-manifold cap.'
    return {e for e,n in edges.items() if n==1}


def source_rims(path,wanted):
    candidates=set().union(*wanted); sparse={};index=0;paint=None;edges=Counter()
    for line in path.open('rb'):
        if line.startswith(b'v '):
            index+=1;p=point(line.split()[1:])
            if p in candidates:sparse[index]=p
        elif line.startswith(b'usemtl '):paint=line.split()[1]
        elif line.startswith(b'f ') and paint in (b'ar_pw_pipe',b'ar_pw_copper'):
            ids=[int(token.split(b'/')[0]) for token in line.split()[1:]]
            for i in range(len(ids)):
                a,b=ids[i],ids[(i+1)%len(ids)]
                if a in sparse and b in sparse:
                    edge=frozenset((sparse[a],sparse[b]))
                    if edge in wanted:edges[edge]+=1
    assert set(edges)==wanted and set(edges.values())=={1},'Rims differ from the installed tubes.'
    return len(edges)


def main():
    stage=OUT/'stage-v1';stage.mkdir(parents=True,exist_ok=False)
    original=ROOT/TARGET
    assert MARKER not in original.read_bytes(),'Caps already installed.'
    model=K.Model();reports=[]
    for row in D.placements():
        report=D.pipe_end_caps(model,**{k:v for k,v in row.items() if k!='name'})
        reports.append({'name':row['name'],**report})
    assert not model.boxes and not model.hulls
    A.configure(model)
    assert all(model.material_overrides[p]==D.MATERIALS[p] for p in model.polygons)
    boundary=cap_edges(model);matched=source_rims(original,boundary)
    fragment=stage/'proof/caps.obj';fragment.parent.mkdir(parents=True)
    K.write_obj(fragment,model,'ares_hall')
    before=sha(original);counts=Counter()
    for line in original.open('rb'):
        key=line.split(maxsplit=1)[0] if line.strip() else b''
        if key in (b'v',b'vt',b'vn'):counts[key]+=1
    tables=[];faces=[]
    for line in fragment.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ')):tables.append(line)
        elif line.startswith(b'usemtl '):faces.append(line)
        elif line.startswith(b'f '):
            tokens=[b'/'.join(str(int(v)+counts[k]).encode() for k,v in zip((b'v',b'vt',b'vn'),token.split(b'/'))) for token in line.split()[1:]]
            faces.append(b'f '+b' '.join(tokens)+b'\n')
    target=stage/TARGET;target.parent.mkdir(parents=True)
    backup=stage/'before'/TARGET;backup.parent.mkdir(parents=True)
    shutil.copyfile(original,backup);shutil.copyfile(original,target)
    with target.open('ab') as f:f.write(MARKER);f.writelines(tables);f.writelines(faces)
    assert sha(original)==before==sha(backup)
    with target.open('rb') as f:assert hashlib.sha256(f.read(original.stat().st_size)).hexdigest()==before
    protected=['Assets/models/maps/ares/ares_hall.vmdl','Assets/models/maps/ares/ares_hall.obj',
        'Assets/models/maps/ares/ares_hall.mtl','Assets/models/maps/ares/pressure-doors-v2/ares_hall.mtl',
        'Assets/models/maps/ares/ares_hall_hulls_default.obj','Assets/models/maps/ares/ares_hall_hulls_metal.obj',
        'Assets/scenes/maps/Ares/ares.scene']
    protected+=[p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/ares/pressure-doors-v3').glob('*.obj') if p.stem in ('wing_west','wing_east','cargo')]
    protected+=[p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/materials/ares/pipework-v1').iterdir() if p.suffix in ('.vmat','.png')]
    sources=['Tools/ares_pipework.py','Tools/ares_close_pipe_ends.py','Tools/map_kit.py','Tools/riverdale_parts.py']
    manifest={'revision':'ares-pipe-end-caps-v1','target':TARGET,'before':before,'after':sha(target),
        'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix(),
        'original_bytes':original.stat().st_size,'original_geometry_prefix_exact':True,
        'protected_sha256':{p:sha(ROOT/p) for p in protected},'source_sha256':{p:sha(ROOT/p) for p in sources},
        'required_source_snippets':{'Tools/ares_map.py':[inspect.getsource(A.pipe_run),inspect.getsource(A.configure)]},
        'runs':reports,'caps':sum(r['caps'] for r in reports),'added_triangles':model.triangle_count(),
        'open_rim_edges_before':matched,'open_rim_edges_after':0,'cap_internal_edges_manifold':True}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('caps','added_triangles','open_rim_edges_before','open_rim_edges_after')}))


if __name__=='__main__':main()
