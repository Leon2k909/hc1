"""Replace the 12 published bistro chairs while retaining all other OBJ bytes."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil

import numpy as np

import map_kit as K
from riverdale_parts import UP, obox, rod, unit, v
import veridant_chair as C
import veridant_materials as VM
from belltower_safe_imports import span
from belltower_compact_obj import compact

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/veridant/chair-v2'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def placements():
    # These four published tables contain all 288 vr_wicker triangles. Other
    # tables present in the source generator have not been published yet.
    rows = []
    for centre, z0, count, seed in (((-520.,800.),128.,3,40),
                                   ((-330.,820.),128.,2,41),
                                   ((220.,-1060.),0.,3,35),
                                   ((-460.,-1240.),0.,4,33)):
        rng = np.random.default_rng(seed)
        for k in range(count):
            angle = 2*np.pi*k/count + rng.uniform(-.3,.3)
            d = np.array((np.cos(angle),np.sin(angle)))
            rows.append((np.array(centre)+d*24, -d, z0))
    return rows


def legacy(model, at, facing, z0):
    f = unit(v(facing[0],facing[1],0))
    s = np.cross(UP,f)
    c = v(at[0],at[1],z0)
    obox(model,c+UP*17.5,f,(16,16,2),'vr_wicker')
    obox(model,c-f*7.5+UP*26,f,(1.4,15,15),'vr_wicker')
    for sa in (-1,1):
        for sb in (-1,1):
            q = c+f*6.5*sa+s*6.5*sb
            rod(model,q,q+UP*16.5,.45,'vr_steel',4)


def quantize(values):
    return tuple(int(round(float(n)*1000)) for n in values)


def replace(source, output, old, addition, append=True):
    lookup, polygons = {}, []
    for paint, faces in old.polygons.items():
        for points, normal in faces:
            vertices = [quantize(K.obj_vector(K.to_world(p)).split()) for p in points]
            number = len(polygons)
            polygons.append(vertices)
            for tri in itertools.combinations(vertices,3):
                key = paint.encode(), frozenset(tri)
                assert key not in lookup
                lookup[key] = number
    wanted = {p for pts in polygons for p in pts}
    sparse, counts, found, removed = {}, Counter(), Counter(), set()
    groups = [Counter() for p in polygons]
    material = None
    source_hash = sha(source)
    for number,line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            counts[b'v'] += 1
            p = quantize(line.split()[1:])
            if p in wanted:
                sparse[counts[b'v']] = p
        elif line.startswith(b'vt '): counts[b'vt'] += 1
        elif line.startswith(b'vn '): counts[b'vn'] += 1
        elif line.startswith(b'usemtl '): material = line.split()[1]
        elif line.startswith(b'f ') and material.decode() in old.polygons:
            indices = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            if all(i in sparse for i in indices):
                key = material, frozenset(sparse[i] for i in indices)
                if key in lookup:
                    removed.add(number)
                    found[lookup[key]] += 1
                    for edge in itertools.combinations(key[1],2):
                        groups[lookup[key]][frozenset(edge)] += 1
    # Every old polygon is covered exactly once, independent of triangulation.
    for i,points in enumerate(polygons):
        boundary = Counter(frozenset((p,points[(k+1)%len(points)])) for k,p in enumerate(points))
        assert found[i] == len(points)-2, ('Missing chair polygon',i,found[i])
        assert Counter({e:n for e,n in groups[i].items() if n==1}) == boundary
    assert len(removed) == old.triangle_count(), (len(removed),old.triangle_count())
    tables, tail = [], []
    for line in addition.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ')): tables.append(line)
        elif line.startswith(b'usemtl '): tail.append(line)
        elif line.startswith(b'f '):
            indices = [b'/'.join(str(int(n)+counts[k]).encode()
                       for k,n in zip((b'v',b'vt',b'vn'),t.split(b'/')))
                       for t in line.split()[1:]]
            tail.append(b'f '+b' '.join(indices)+b'\n')
    retained = hashlib.sha256()
    with output.open('wb') as stream:
        for number,line in enumerate(source.open('rb')):
            if number not in removed:
                retained.update(line)
                stream.write(line)
        if append:
            # Existing partial edits can have tables AFTER the first usemtl.
            # Append after all old tables so their absolute indices never shift.
            stream.writelines(tables)
            stream.writelines(tail)
    assert sha(source) == source_hash
    actual = output.read_bytes()
    if append:
        actual = actual.replace(b''.join(tables),b'',1)[:-len(b''.join(tail))]
    assert hashlib.sha256(actual).hexdigest() == retained.hexdigest()
    return {'removed_triangles':len(removed), 'retained_obj_bytes_exact':True,
            'retained_sha256':retained.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',default='stage-v1')
    parser.add_argument('--repair-from',help='Repartition an already-installed guarded revision')
    parser.add_argument('--replay-table',help='Preserve the exact intervening table revision when repairing an initial import')
    args = parser.parse_args()
    assert args.stage.replace('-','').isalnum()
    stage = OUT/args.stage
    assert not stage.exists(), 'Keep each staged revision'
    stage.mkdir(parents=True)
    prior = None
    if args.repair_from:
        prior_stage = OUT/args.repair_from
        prior = json.loads((prior_stage/'manifest.json').read_text())
        # Another scoped prop edit may have landed since this revision. Match
        # and remove our installed chair triangles from the latest files rather
        # than restoring a shared backup and losing the intervening change.
    table_stage = OUT.parent/'table-v2'/args.replay_table if args.replay_table else None
    table_revision = json.loads((table_stage/'manifest.json').read_text()) if table_stage else None
    model, old = K.Model(), K.Model()
    rows = placements()
    for at,facing,z0 in rows:
        C.build_into(model,at,facing,z0)
        legacy(old,at,facing,z0)
    model.tile_overrides = {paint:VM.TILES.get(paint,64.) for paint in model.polygons}
    assert not model.boxes and not model.hulls
    assert not old.boxes and not old.hulls
    assert all(np.isfinite(n).all() for normals in model.polygon_normals.values() for n in normals)
    assert all(np.isfinite(p).all() for faces in model.polygons.values() for pts,n in faces for p in pts)
    piece = stage/'chairs.obj'
    new_triangles = K.write_obj(piece,model,'veridant_chairs_v2')
    canonical = Path('Assets/models/maps/veridant/veridant_dress.obj')
    vmdl = ROOT/canonical.with_suffix('.vmdl')
    document = vmdl.read_text()
    render_document = document.split('_class = "PhysicsShapeList"')[0]
    imports = [Path('Assets')/path for path in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', render_document)]
    input_hashes = {p.as_posix():sha(ROOT/p) for p in dict.fromkeys([canonical,canonical.with_suffix('.vmdl'),*imports])}
    targets, replacements = [], {}
    for relative in dict.fromkeys([canonical,*imports]):
        # The active model can already have been partitioned by another scoped
        # prop edit. Patch the actual render import as well as the canonical OBJ.
        source = ROOT/relative
        if table_revision and prior and relative.as_posix() in prior['files']:
            # Replay the recorded table-only edit against our pre-import bytes.
            # Both sides of this chain are guarded; no other edit is discarded.
            rel = relative.as_posix()
            table_item = table_revision['files'][rel]
            assert table_item['before'] == prior['files'][rel]['after'], ('Unexpected intervening edit',rel)
            assert sha(ROOT/relative) == table_item['after'], ('Newer shared edit',rel)
            baseline = prior_stage/'before'/relative
            assert sha(baseline) == prior['files'][rel]['before']
            import veridant_table as T
            table_old = K.Model()
            for e,n,z in table_revision['placements'][rel]:
                T.legacy_top(table_old,(e,n),z)
            table_piece = table_stage/'pieces'/(rel.replace('/','--')+'.obj')
            replayed = stage/'rebase-input'/relative
            replayed.parent.mkdir(parents=True,exist_ok=True)
            replace(baseline,replayed,table_old,table_piece,append=True)
            source = replayed
        if b'usemtl vr_wicker\n' not in source.read_bytes():
            continue
        target = stage/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        replacements[relative.as_posix()] = replace(source,target,model if prior and not table_revision else old,piece,append=relative==canonical)
        if relative != canonical:
            temporary = target.with_suffix('.uncompacted.obj')
            target.rename(temporary)
            replacements[relative.as_posix()]['compaction'] = compact(temporary,target,deduplicate=True)
            counts = Counter(l.split()[0] for l in target.open() if l.startswith(('v ','vt ','vn ')))
            assert max(counts.values()) < 65536, counts
        targets.append(target)
    assert targets and canonical.as_posix() in replacements
    # Keep the new chair imports bounded and separate from the existing props.
    # Small tables also avoid pushing a shared import toward index limits.
    chunks = []
    for start in range(0,len(rows),6):
        chunk = K.Model()
        for at,facing,z0 in rows[start:start+6]:
            C.build_into(chunk,at,facing,z0)
        chunk.tile_overrides = {paint:VM.TILES.get(paint,64.) for paint in chunk.polygons}
        path = stage/f'Assets/models/maps/veridant/chair-v2/chairs-{start//6}.obj'
        path.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(path,chunk,path.stem)
        counts = Counter(l.split()[0] for l in path.open() if l.startswith(('v ','vt ','vn ')))
        assert max(counts.values()) < 65536, counts
        targets.extend([path,path.with_suffix('.mtl')])
        chunks.append(path.relative_to(stage/'Assets').as_posix())
    a,b = span(document,'_class = "RenderMeshList"')
    render = document[a:b]
    x,y = span(render,'_class = "RenderMeshFile"')
    template = render[x:y]
    new_nodes = []
    for index,path in enumerate(chunks):
        node = re.sub(r'name = "[^"]+"',f'name = "veridant_chairs_v2_{index}"',template,count=1)
        node = re.sub(r'filename = "[^"]+"',f'filename = "{path}"',node,count=1)
        new_nodes.append(node)
    end = render.rfind(']')
    prefix = render[:end].rstrip()
    new_render = prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(new_nodes)+'\n'+render[end:]
    updated = document[:a]+new_render+document[b:]
    x,y = span(document,'_class = "PhysicsShapeList"')
    u,w = span(updated,'_class = "PhysicsShapeList"')
    assert document[x:y] == updated[u:w]
    staged_vmdl = stage/canonical.with_suffix('.vmdl')
    staged_vmdl.write_text(updated)
    targets.append(staged_vmdl)
    materials = stage/'Assets/materials/veridant'
    materials.mkdir(parents=True)
    VM.build('vr_wicker',materials)
    files = {}
    for path in [*targets,*materials.iterdir()]:
        rel = path.relative_to(stage).as_posix()
        source = ROOT/rel
        before = input_hashes.get(rel,sha(source) if source.exists() else None)
        if before:
            backup = stage/'before'/rel
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,backup)
        files[rel] = {'before':before,'after':sha(path),
                      'source':path.relative_to(ROOT).as_posix()}
    protected_files = [ROOT/'Assets/scenes/maps/Veridant/veridant.scene',
                       ROOT/'Assets/models/maps/veridant/veridant_dress.mtl',
                       *list((ROOT/'Assets/models/maps/veridant').glob('veridant_dress_hulls_*.obj')),
                       *[ROOT/p for p in imports if p.as_posix() not in replacements]]
    protected = {p.relative_to(ROOT).as_posix():sha(p) for p in protected_files}
    single = K.Model()
    C.build_into(single,(0,0),(1,0))
    vertices = np.array([p for faces in single.polygons.values() for pts,n in faces for p in pts])
    assert abs(vertices[:,2].min()) < .001, vertices[:,2].min()
    assert vertices[:,2].max() < 34
    report = {'revision':'veridant-chair-v2', 'files':files, 'protected':protected,
              'replacement':replacements, 'instances':len(rows),
              'new_triangles':new_triangles,'triangles_per_chair':single.triangle_count(),
              'chair_imports':chunks,'physics_bytes_exact':True,
              'placements':[{'at':at.tolist(),'facing':f.tolist(),'z0':z} for at,f,z in rows],
              'bounds':{'min':vertices.min(axis=0).tolist(),'max':vertices.max(axis=0).tolist()}}
    for rel,data in files.items():
        assert (sha(ROOT/rel) if (ROOT/rel).exists() else None) == data['before'], rel
    for rel,digest in input_hashes.items():
        assert sha(ROOT/rel) == digest, ('Shared source changed during staging',rel)
    (stage/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('instances','new_triangles','triangles_per_chair','replacement','bounds')}))


if __name__ == '__main__':
    main()
