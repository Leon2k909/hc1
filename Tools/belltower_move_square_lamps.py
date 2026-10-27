"""Translate the two northern plaza lamps and their hulls without rebuilding the town."""
from collections import Counter
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import belltower_map as B
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/lamp-placement'
STAGE=OUT/'stage-v1'
SHIFT=190.


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def geometry(model):
    wanted=Counter()
    for paint,rows in model.polygons.items():
        for points,normal in rows:
            pts=[K.obj_vector(K.to_world(p)).encode() for p in points]
            for i in range(1,len(pts)-1):wanted[(paint.encode(),frozenset((pts[0],pts[i],pts[i+1])))]+=1
    return wanted


def record(path,report):
    relative=path.relative_to(ROOT).as_posix()
    backup=STAGE/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,backup)
    return {**report,'before':sha(path),'after':sha(STAGE/relative),
        'source':(STAGE/relative).relative_to(ROOT).as_posix(),
        'backup':backup.relative_to(ROOT).as_posix()}


def patch_render(path,wanted):
    desired=set().union(*(points for paint,points in wanted));paints={p for p,points in wanted}
    sparse={};count=0;faces=0;material=None;matches={};found=Counter();saw_face=False
    for number,line in enumerate(path.open('rb')):
        if line.startswith(b'v '):
            assert not saw_face,'Interleaved position tables require a different patch.'
            count+=1;point=line[2:].strip()
            if point in desired:sparse[count]=point
        elif line.startswith(b'usemtl '):material=line.split()[1]
        elif line.startswith(b'f '):
            saw_face=True;faces+=1
            if material not in paints:continue
            tokens=[token.split(b'/') for token in line.split()[1:]]
            indices=[int(t[0]) for t in tokens]
            if not all(i in sparse for i in indices):continue
            key=(material,frozenset(sparse[i] for i in indices))
            if key in wanted:matches[number]=tokens;found[key]+=1
    if not matches:return None,found
    used={int(t[0]) for row in matches.values() for t in row}
    moved={index:count+i+1 for i,index in enumerate(sorted(used))}
    extra=[]
    for index in sorted(used):
        x,y,z=map(float,sparse[index].split());extra.append(f'v {x:.3f} {y:.3f} {z+SHIFT:.3f}\n'.encode())
    target=STAGE/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
    inserted=False;unrelated_before=hashlib.sha256();unrelated_after=hashlib.sha256()
    with target.open('wb') as output:
        for number,line in enumerate(path.open('rb')):
            if not inserted and line.startswith((b'usemtl ',b'f ')):
                output.writelines(extra);inserted=True
            if number in matches:
                tokens=[b'/'.join((str(moved[int(t[0])]).encode(),*t[1:])) for t in matches[number]]
                output.write(b'f '+b' '.join(tokens)+b'\n')
            else:
                unrelated_before.update(line);output.write(line);unrelated_after.update(line)
    assert inserted and unrelated_before.digest()==unrelated_after.digest()
    row=record(path,{'translated_faces':len(matches),'new_position_entries':len(extra),
        'triangles_before':faces,'triangles_after':faces,'unrelated_source_bytes_exact':True,
        'uv_and_normal_bytes_exact':True,'unrelated_bytes_sha256':unrelated_before.hexdigest()})
    return row,found


def patch_hulls(path,model):
    wanted=Counter(K.obj_vector(K.to_world(p)).encode() for points,surface in model.hulls for p in points)
    found=Counter();target=STAGE/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
    changed=0
    with target.open('wb') as output:
        for line in path.open('rb'):
            if line.startswith(b'v ') and line[2:].strip() in wanted:
                found[line[2:].strip()]+=1;x,y,z=map(float,line.split()[1:])
                line=f'v {x:.3f} {y:.3f} {z+SHIFT:.3f}\n'.encode();changed+=1
            output.write(line)
    assert found==wanted and changed==28,(path,changed)
    return record(path,{'translated_collision_vertices':changed,'collision_hulls_moved':2,
        'all_other_hull_vertices_and_faces_exact':True})


def main():
    STAGE.mkdir(parents=True,exist_ok=False)
    assert '( -420, 520 )' in inspect.getsource(B.street_props)
    old=K.Model();B.lamp_post(old,(-420,330))
    assert len(old.hulls)==2 and not old.boxes
    result={'revision':'belltower-square-lamp-placement-v1','old_plan_centres':[[-420,330],[420,330]],
        'new_plan_centres':[[-420,520],[420,520]],'shift_world':[SHIFT,0,0],
        'lamps':2,'files':{},'protected_sha256':{},'source_sha256':{},'models':{}}
    protected=['Assets/scenes/maps/Belltower/belltower.scene']
    for side,model in (('west',old),('east',old.mirrored())):
        wanted=geometry(model);canonical=ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row,found=patch_render(canonical,wanted)
        assert found==wanted,('Canonical lamp geometry differs',side,sum(found.values()),sum(wanted.values()))
        result['files'][canonical.relative_to(ROOT).as_posix()]=row
        vmdl=canonical.with_suffix('.vmdl');protected.append(vmdl.relative_to(ROOT).as_posix())
        paths=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text())
        matched=Counter();changed=[]
        for resource in paths:
            relative='Assets/'+resource
            if re.search(r'_(iron_black|lamp_bulb|lamp_reflector|lantern_glass)\.obj$',resource):
                row,found=patch_render(ROOT/relative,wanted);matched.update(found)
                if row:result['files'][relative]=row;changed.append(relative)
                else:protected.append(relative)
            elif not resource.endswith('_hulls_metal.obj'):protected.append(relative)
        assert matched==wanted,('Referenced lamp geometry differs',side,sum(matched.values()),sum(wanted.values()))
        hull=ROOT/f'Assets/models/maps/belltower/belltower_{side}_hulls_metal.obj'
        result['files'][hull.relative_to(ROOT).as_posix()]=patch_hulls(hull,model)
        result['models'][side]={'lamp_triangles':sum(wanted.values()),'changed_render_imports':changed,
            'collision_hulls_moved':2,'modeldoc_unchanged':True}
        print(json.dumps({'side':side,**result['models'][side]}),flush=True)
    result['protected_sha256']={p:sha(ROOT/p) for p in protected}
    result['source_sha256']={p:sha(ROOT/p) for p in ('Tools/belltower_map.py','Tools/belltower_move_square_lamps.py','Tools/belltower_detail.py','Tools/map_kit.py')}
    assert all(sha(ROOT/p)==row['before'] for p,row in result['files'].items())
    (STAGE/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'lamps':2,'files':len(result['files']),'move_inches':SHIFT,'collision_hulls':4}))


if __name__=='__main__':main()
