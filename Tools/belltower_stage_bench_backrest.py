"""Stage only the 36 rear bench uprights; preserve all unrelated OBJ bytes."""
from collections import Counter
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

import numpy as np

import belltower_compact_obj as C
import belltower_detail as D
import belltower_furniture as F
import belltower_map as B
from belltower_stage_bench_arms import geometry, placements, rows, key
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/bench-backrest-v3'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def patch(source, wanted, replacement, target, backup):
    before = sha(source)
    data = C.tables(source)
    counts = {k:len(v)-1 for k,v in data.items()}
    found = Counter()
    removed = set()
    material = None
    face_count = 0
    for number,line in enumerate(source.open('rb')):
        if line.startswith(b'usemtl '): material = line.split()[1]
        elif line.startswith(b'f '):
            face_count += 1
            if material != b'iron_black': continue
            corners = [tuple(data[k][i] for k,i in zip(C.KINDS,indices))
                       for indices in C.face_tokens(line,counts)]
            signature = key(material,corners)
            if signature in wanted:
                found[signature] += 1
                removed.add(number)
    if not removed:
        assert not replacement
        return None,found
    assert found <= wanted
    target.parent.mkdir(parents=True,exist_ok=True)
    backup.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists() and not backup.exists()
    shutil.copyfile(source,backup)
    append = {k:[] for k in C.KINDS}
    caches = {k:{} for k in C.KINDS}
    new_faces = []
    for signature,corners in replacement:
        assert signature[0] == b'iron_black'
        tokens = []
        for corner in corners:
            indices = []
            for kind,value in zip(C.KINDS,corner):
                if value not in caches[kind]:
                    append[kind].append(value)
                    caches[kind][value] = counts[kind]+len(append[kind])
                indices.append(str(caches[kind][value]).encode())
            tokens.append(b'/'.join(indices))
        new_faces.append(b'f '+b' '.join(tokens)+b'\n')
    preserved = hashlib.sha256()
    inserted = False
    with target.open('wb') as output:
        for number,line in enumerate(source.open('rb')):
            if not inserted and line.startswith(b'usemtl '):
                for kind in C.KINDS: output.writelines(append[kind])
                inserted = True
            if number not in removed:
                output.write(line)
                preserved.update(line)
        output.write(b'usemtl iron_black\n')
        output.writelines(new_faces)
    assert inserted and sha(source)==before and sha(backup)==before
    assert target.read_bytes().endswith(b'usemtl iron_black\n'+b''.join(new_faces))
    return {'before':before,'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix(),'old_support_triangles_removed':len(removed),
            'new_support_triangles':len(new_faces),'triangles_before':face_count,
            'triangles_after':face_count-len(removed)+len(new_faces),
            'all_unrelated_source_bytes_preserved':True,
            'unrelated_source_bytes_sha256':preserved.hexdigest()},found


def check_clearance():
    p = B.Place((0,0,0))
    support = K.Model()
    F.bench_back_support(support,p,0)
    points = np.array([q for polygons in support.polygons.values() for polygon,_ in polygons for q in polygon])
    rake = np.radians(8)
    normal = np.array((0,np.cos(rake),-np.sin(rake)))
    rear_plane = np.dot(np.array((0,7.4,18)),normal)+.7
    # Every support point above the seat stays behind all three coplanar backs.
    clearance = (points@normal-rear_plane).min()
    assert clearance >= .039999
    # Clip each support face at seat height; its remaining vertices stay aft.
    for polygons in support.polygons.values():
        for polygon,_ in polygons:
            below = [q for q in polygon if q[2]<=18]
            for a,b in zip(polygon,polygon[1:]+polygon[:1]):
                if (a[2]<18<b[2]) or (b[2]<18<a[2]):
                    below.append(a+(b-a)*(18-a[2])/(b[2]-a[2]))
            assert not below or min(q[1] for q in below)>8.82
    assert points[:,2].max()<31.3+2.25*np.cos(rake)-.7*np.sin(rake)
    return {'minimum_backrest_plane_clearance_inches':float(clearance),
            'seat_intersection_free':True,'upright_top_below_top_slat':True,
            'backrest_and_upright_rake_degrees':8}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',type=int,default=2)
    args = parser.parse_args()
    stage = OUT/f'stage-r{args.revision}'
    backup = OUT/f'before-r{args.revision}'
    assert not stage.exists(), 'Retain prior evidence and use a fresh revision.'
    stage.mkdir(parents=True)
    spec = importlib.util.spec_from_file_location('bench_v3_before',OUT/'before-source/Tools/belltower_furniture.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    old,new,old_full,new_full = [K.Model() for _ in range(4)]
    for centre,yaw,length,z in placements():
        p = B.Place((*centre,z),yaw)
        previous.bench(old_full,p,length)
        F.bench(new_full,p,length)
        for x in (-length/2+6,length/2-6):
            previous.beam(old,p.at((x,5.5,12)),p.at((x,11.4,34)),(1.3,1.4),F.IRON,.2)
            F.bench_back_support(new,p,x)
    a,b,c,d = map(geometry,(old_full,new_full,old,new))
    assert a-b==c-d and b-a==d-c, 'A bench part other than its rear supports changed.'
    assert not old.boxes and not new.boxes and not old.props and not new.props
    result = {'revision':'bench-backrest-v3','stage_revision':args.revision,'benches':18,'rear_supports':36,
              'clearance':check_clearance(),'only_rear_supports_changed':True,'collision_unchanged':True,
              'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
              'files':{},'models':{},'source_sha256':{},'vmdl_guards':{}}
    for name in ('Tools/belltower_furniture.py','Tools/belltower_stage_bench_backrest.py','Tools/map_kit.py'):
        result['source_sha256'][name] = sha(ROOT/name)
    for side in ('west','east'):
        old_model,new_model = (old,new) if side=='west' else (old.mirrored(),new.mirrored())
        for label,model in (('old',old_model),('new',new_model)):
            model.tile_overrides.update(D.TILES)
            K.write_obj(stage/f'{side}-{label}.obj',model,f'belltower_{side}')
        old_rows = rows(stage/f'{side}-old.obj')
        new_rows = rows(stage/f'{side}-new.obj')
        wanted = Counter(row[0] for row in old_rows)
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        row,found = patch(canonical,wanted,new_rows,stage/canonical.relative_to(ROOT),backup/canonical.relative_to(ROOT))
        assert found==wanted, ('Canonical support mismatch',side,sum(found.values()),sum(wanted.values()))
        result['files'][canonical.relative_to(ROOT).as_posix()] = row
        vmdl = canonical.with_suffix('.vmdl')
        result['vmdl_guards'][vmdl.relative_to(ROOT).as_posix()] = sha(vmdl)
        resources = re.findall(r'filename\s*=\s*"([^"]+\.obj)"',vmdl.read_text())
        candidates = [ROOT/'Assets'/resource for resource in resources if resource.endswith('_iron_black.obj')]
        matches = []
        for source in candidates:
            signatures = Counter(signature for signature,_ in rows(source) if signature in wanted)
            if signatures: matches.append((source,signatures))
        # Current bounded imports contain each half's complete set of rear supports.
        # Refuse to guess if future repartitioning splits the set across pieces.
        assert len(matches)==1 and matches[0][1]==wanted, ('Bounded support partition changed',side)
        source = matches[0][0]
        row,found = patch(source,wanted,new_rows,stage/source.relative_to(ROOT),backup/source.relative_to(ROOT))
        assert found==wanted and row['triangles_after']<=100000
        result['files'][source.relative_to(ROOT).as_posix()] = row
        result['models'][side] = {'old_support_triangles':len(old_rows),'new_support_triangles':len(new_rows),
                                  'bounded_import':source.relative_to(ROOT).as_posix(),
                                  'model_description_and_physics_unchanged':True}
    for group in ('source_sha256','vmdl_guards'):
        assert all(sha(ROOT/p)==h for p,h in result[group].items())
    assert all(sha(ROOT/p)==row['before'] for p,row in result['files'].items())
    (stage/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'files':len(result['files']),'benches':18,'supports':36,
                      'clearance':result['clearance'],'models':result['models']}))


if __name__=='__main__': main()
