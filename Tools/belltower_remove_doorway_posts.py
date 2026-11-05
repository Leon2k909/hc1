"""Stage removal of the redundant mirrored doorway lamp posts, preserving other art."""
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import tempfile
import belltower_map as B
import map_kit as K
from belltower_move_square_lamps import geometry, sha

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(tempfile.gettempdir())/'belltower-doorway-post-removal-v1'
STAGE=OUT/'stage'

def record(path,data,report):
    rel=path.relative_to(ROOT).as_posix()
    target=STAGE/rel
    backup=STAGE/'before'/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,backup)
    target.write_bytes(data)
    return dict(report,before=sha(path),after=sha(target),source=target.as_posix(),backup=backup.as_posix())

def render(path,wanted):
    desired=set().union(*(points for paint,points in wanted))
    paints={paint for paint,points in wanted}
    sparse={}; number=0; material=None; found=Counter(); removed=set(); faces=0
    for index,line in enumerate(path.open('rb')):
        if line.startswith(b'v '):
            number+=1
            if line[2:].strip() in desired:sparse[number]=line[2:].strip()
        elif line.startswith(b'usemtl '):material=line.split()[1]
        elif line.startswith(b'f '):
            faces+=1
            if material not in paints:continue
            ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
            if not all(i in sparse for i in ids):continue
            key=(material,frozenset(sparse[i] for i in ids))
            if key in wanted:found[key]+=1;removed.add(index)
    if not removed:return None,found
    rel=path.relative_to(ROOT).as_posix()
    target=STAGE/rel;backup=STAGE/'before'/rel
    target.parent.mkdir(parents=True,exist_ok=True);backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,backup)
    with target.open('wb') as output:
        for index,line in enumerate(path.open('rb')):
            if index not in removed:output.write(line)
    return dict(removed_triangles=len(removed),triangles_before=faces,triangles_after=faces-len(removed),all_other_bytes_exact=True,before=sha(path),after=sha(target),source=target.as_posix(),backup=backup.as_posix()),found

def hulls(path,model):
    wanted=Counter(K.obj_vector(K.to_world(p)).encode() for points,surface in model.hulls for p in points)
    lines=path.read_bytes().splitlines(keepends=True)
    old={};found=Counter();removed=set();remap={};n=0;out=[];faces=0
    for line in lines:
        if not line.startswith(b'v '):continue
        n+=1;point=line[2:].strip();old[n]=point
        if point in wanted:removed.add(n);found[point]+=1
        else:remap[n]=len(remap)+1
    assert found==wanted and len(removed)==28,(path,found-wanted,wanted-found)
    n=0
    before_faces=Counter();after_faces=Counter()
    for line in lines:
        if line.startswith(b'v '):
            n+=1
            if n not in removed:out.append(line)
        elif line.startswith(b'f '):
            ids=[int(t) for t in line.split()[1:]]
            if any(i in removed for i in ids):
                assert all(i in removed for i in ids),'A hull shares lamp vertices'
                faces+=1;continue
            before_faces[tuple(old[i] for i in ids)]+=1
            out.append(b'f '+b' '.join(str(remap[i]).encode() for i in ids)+b'\n')
            after_faces[tuple(old[i] for i in ids)]+=1
        else:out.append(line)
    assert before_faces==after_faces
    return record(path,b''.join(out),{'removed_collision_vertices':28,'removed_collision_triangles':faces,'removed_collision_hulls':2,'other_collision_geometry_exact':True})

def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    model=K.Model();B.lamp_post(model,(-1870,450))
    result={'revision':'belltower-doorway-post-removal-v1','lamps_removed':2,'plan_centres':[[-1870,450],[1870,450]],'files':{},'protected_sha256':{},'source_sha256':{}}
    protected=['Assets/scenes/maps/Belltower/belltower.scene']
    for side,m in [('west',model),('east',model.mirrored())]:
        wanted=geometry(m)
        canonical=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row,found=render(canonical,wanted)
        assert found==wanted,(side,'canonical',sum(found.values()),sum(wanted.values()))
        result['files'][canonical.relative_to(ROOT).as_posix()]=row
        vmdl=canonical.with_suffix('.vmdl');protected.append(vmdl.relative_to(ROOT).as_posix())
        matched=Counter()
        for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text()):
            relative='Assets/'+resource
            if re.search(r'_(iron_black|lamp_bulb|lamp_reflector|lantern_glass)\.obj$',resource):
                row,found=render(ROOT/relative,wanted);matched.update(found)
                if row:result['files'][relative]=row
                else:protected.append(relative)
            elif not resource.endswith('_hulls_metal.obj'):protected.append(relative)
        assert matched==wanted,(side,'referenced',sum(matched.values()),sum(wanted.values()))
        path=ROOT/f'Assets/models/maps/belltower/belltower_{side}_hulls_metal.obj'
        result['files'][path.relative_to(ROOT).as_posix()]=hulls(path,m)
    result['protected_sha256']={p:sha(ROOT/p) for p in protected}
    result['source_sha256']={p:sha(ROOT/p) for p in ['Tools/belltower_map.py','Tools/belltower_remove_doorway_posts.py','Tools/belltower_detail.py','Tools/map_kit.py']}
    (STAGE/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'files':len(result['files']),'render_triangles_removed_per_side':sum(geometry(model).values()),'collision_hulls_removed':4,'other_geometry_preserved':True}))

if __name__=='__main__':main()
