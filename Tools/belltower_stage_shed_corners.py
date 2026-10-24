"""Stage only six sheds' timber, preserving unrelated town and import bytes."""
from collections import Counter
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_gardens as G
import belltower_furniture as F

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'output/belltower/shed-corners-v1'
SHEDS = ((-1840,-1720,-1440,-1340,'+n',False),
         (-420,-300,-1440,-1360,'+n',False),
         (-1440,-1380,-1090,-1030,'+e',True))
PAINTS = {F.WOOD, F.DARK}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def triangles(model):
    for paint, faces in model.polygons.items():
        for j, (points, normal) in enumerate(faces):
            uv = model.polygon_uvs.get((paint,j))
            normals = model.polygon_normals.get((paint,j))
            for i in range(1,len(points)-1):
                indices = (0,i,i+1)
                p = [points[k] for k in indices]
                key = (paint, frozenset(K.obj_vector(K.to_world(q)) for q in p))
                yield key, p, normal, [uv[k] for k in indices] if uv is not None else None, [normals[k] for k in indices] if normals is not None else None


def difference():
    spec = importlib.util.spec_from_file_location('shed_corners_original_gardens',BASE/'gardens-before.py')
    original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    models = []
    for module in (original,G):
        model = K.Model()
        for e0,e1,n0,n1,door,small in SHEDS:
            module.shed(model,e0,e1,n0,n1,-48,door,small)
        D.configure(model); models.append(model)
    before, after = [Counter(row[0] for row in triangles(model)) for model in models]
    removed, added = before-after, after-before
    assert {p for p,_ in removed} <= PAINTS and {p for p,_ in added} <= PAINTS
    piece = K.Model(); remaining = added.copy()
    for key,points,normal,uv,normals in triangles(models[1]):
        if remaining[key]:
            piece.polygon(key[0],points,normal=normal,uv=uv,normals=normals); remaining[key] -= 1
    assert not +remaining and not piece.boxes and not piece.hulls and not piece.props
    D.configure(piece)
    return removed,piece


def scan(path, wanted):
    vertices = {p for _, face in wanted for p in face}
    positions = {}; counts = dict(v=0,vt=0,vn=0); material = None
    found = Counter(); drop = set(); faces = 0
    for line_number,line in enumerate(path.open('rb')):
        if line.startswith(b'v '):
            counts['v'] += 1; p = line[2:].strip().decode()
            if p in vertices: positions[counts['v']] = p
        elif line.startswith(b'vt '): counts['vt'] += 1
        elif line.startswith(b'vn '): counts['vn'] += 1
        elif line.startswith(b'usemtl '): material = line[7:].strip().decode()
        elif line.startswith(b'f '):
            faces += 1
            if material not in PAINTS: continue
            coords = [positions.get(int(token.split(b'/')[0])) for token in line.split()[1:]]
            if None in coords: continue
            key = material,frozenset(coords)
            if key in wanted:
                found[key] += 1; drop.add(line_number)
    return dict(counts=counts,found=found,drop=drop,faces=faces)


def append_bytes(piece_path, counts):
    output = []
    for line in piece_path.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ',b'usemtl ')): output.append(line)
        elif line.startswith(b'f '):
            tokens = []
            for token in line.split()[1:]:
                a,b,c = map(int,token.split(b'/'))
                tokens.append(f'{a+counts["v"]}/{b+counts["vt"]}/{c+counts["vn"]}')
            output.append(('f '+' '.join(tokens)+'\n').encode())
    return b''.join(output)


def patch_file(source, out, row, addition=None):
    relative = source.relative_to(ROOT); target = out/relative; backup = out/'before'/relative
    target.parent.mkdir(parents=True,exist_ok=True); backup.parent.mkdir(parents=True,exist_ok=True)
    before = sha(source); preserved = hashlib.sha256()
    with source.open('rb') as src, target.open('wb') as dest, backup.open('wb') as saved:
        for i,line in enumerate(src):
            saved.write(line)
            if i not in row['drop']: dest.write(line); preserved.update(line)
        if addition is not None: dest.write(append_bytes(addition,row['counts']))
    assert sha(source) == before == sha(backup), 'Shared town changed while staging'
    return dict(before=before,after=sha(target),removed_faces=len(row['drop']),
                retained_bytes_sha256=preserved.hexdigest())


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--revision',default='r1')
    args = parser.parse_args(); assert re.fullmatch(r'[a-z0-9-]+',args.revision)
    out = BASE/args.revision/'stage'; assert not (out/'manifest.json').exists()
    out.mkdir(parents=True,exist_ok=True)
    removed,piece = difference()
    report = dict(revision='shed-corners-v1',stage_revision=args.revision,sheds=6,files={},input_guards={},
                  removed_triangles_per_half=sum(removed.values()),added_triangles_per_half=piece.triangle_count(),
                  scene_sha256=sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
                  collision_unchanged=True,roof_and_hardware_unchanged=True,all_unrelated_face_bytes_preserved=True,
                  source_sha256={p:sha(ROOT/p) for p in ('Tools/belltower_shed_wood.py','Tools/belltower_gardens.py',
                    'Tools/belltower_stage_shed_corners.py','Tools/map_kit.py','Tools/belltower_furniture.py',
                    'output/belltower/shed-corners-v1/gardens-before.py')},models={})
    for side in ('west','east'):
        new = piece if side=='west' else piece.mirrored()
        wanted = removed
        if side == 'east':
            # OBJ position = (-e,z,n), so east/west mirroring negates its first coordinate.
            wanted = Counter()
            for (paint,face),count in removed.items():
                reflected = frozenset(f'{-float(p.split()[0]):.3f} {float(p.split()[1]):.3f} {float(p.split()[2]):.3f}' for p in face)
                wanted[paint,reflected] += count
        name = 'belltower_'+side
        full_piece = out/(name+'-timber.obj'); K.write_obj(full_piece,new,name)
        source = ROOT/f'Assets/models/maps/belltower/{name}.obj'; row = scan(source,wanted)
        assert row['found'] == wanted,(side,'canonical missing',sum((wanted-row['found']).values()))
        report['files'][source.relative_to(ROOT).as_posix()] = patch_file(source,out,row,full_piece)
        vmdl = source.with_suffix('.vmdl'); vmdl_hash = sha(vmdl)
        mtl = source.with_suffix('.mtl')
        report['input_guards'][vmdl.relative_to(ROOT).as_posix()] = vmdl_hash
        report['input_guards'][mtl.relative_to(ROOT).as_posix()] = sha(mtl)
        resources = re.findall(r'filename = "([^"]+\.obj)"',vmdl.read_text())
        resources = [p for p in resources if any(p.endswith('_'+paint+'.obj') for paint in PAINTS)]
        scans = [(ROOT/'Assets'/p,scan(ROOT/'Assets'/p,wanted)) for p in resources]
        found = sum((r['found'] for _,r in scans),Counter())
        assert found == wanted,(side,'bounded imports missing',sum((wanted-found).values()),sum((found-wanted).values()))
        destinations = {}
        for paint in sorted(PAINTS):
            candidates = [(p,r) for p,r in scans if p.name.endswith('_'+paint+'.obj')]
            destination,r = min(candidates,key=lambda q:q[1]['faces']-len(q[1]['drop']))
            addition = K.Model(); addition.polygons[paint] = new.polygons[paint]
            for (p,i),uv in new.polygon_uvs.items():
                if p==paint:addition.polygon_uvs[p,i]=uv
            for (p,i),normals in new.polygon_normals.items():
                if p==paint:addition.polygon_normals[p,i]=normals
            D.configure(addition)
            temp = out/(name+'-'+paint+'.obj'); K.write_obj(temp,addition,name)
            total = r['faces']-len(r['drop'])+addition.triangle_count()
            assert total <= 100_000,(side,paint,total)
            destinations[destination] = (temp,total)
        imports = []
        for path,r in scans:
            if not r['drop'] and path not in destinations:continue
            add,total = destinations.get(path,(None,r['faces']-len(r['drop'])))
            assert total > 0, 'Do not leave an empty render import'
            relative = path.relative_to(ROOT).as_posix()
            report['files'][relative] = patch_file(path,out,r,add)
            imports.append(dict(asset=relative,triangles_after=total,removed=len(r['drop']),receives_new_timber=add is not None))
        assert sha(vmdl)==vmdl_hash
        report['models'][side]=dict(imports=imports,vmdl_unchanged=True,materials_unchanged=True)
        print(json.dumps(dict(side=side,removed=sum(wanted.values()),added=new.triangle_count(),imports=imports)),flush=True)
    assert all(sha(ROOT/p)==record['before'] for p,record in report['files'].items())
    assert all(sha(ROOT/p)==digest for p,digest in report['input_guards'].items())
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=str(out),files=len(report['files']),sheds=6)),flush=True)


if __name__=='__main__':main()
