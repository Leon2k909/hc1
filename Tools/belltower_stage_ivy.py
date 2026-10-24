"""Stage a surgical replacement of existing wall-ivy planes with branching ivy.

Never regenerates the town and never writes live Assets. Native editor import
publishes these files after checking their originals. Preserve bounded imports.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import shutil
import argparse
import numpy as np
import map_kit as K
import belltower_ivy as I
import belltower_compact_obj as C

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/ivy-3d-v1/final'
STAGE = OUT/'stage'
OLD = {'ivy_climb', 'ivy_hang'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def plan(vector):
    a,b,c = map(float, vector)
    return np.array((-a,c,b))


def patches(path):
    vertices = [None]; normals = [None]; faces = []
    for line in path.read_text().splitlines():
        if line.startswith('v '): vertices.append(plan(line.split()[1:]))
        elif line.startswith('vn '): normals.append(plan(line.split()[1:]))
        elif line.startswith('f '): faces.append([list(map(int,t.split('/'))) for t in line.split()[1:]])
    assert len(faces)%2 == 0
    result = []
    for a,b in zip(faces[::2],faces[1::2]):
        ids = list(dict.fromkeys(t[0] for t in a+b))
        assert len(ids)==4 and len({t[2] for t in a+b})==1
        pts = [vertices[k] for k in ids]
        assert len({p[2] for p in pts})==2
        result.append((pts, normals[a[0][2]]))
    return result


def stage_file(relative, data):
    original = ROOT/relative
    backup = OUT/'before'/relative
    target = STAGE/relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not backup.exists(), ('Keep the original evidence', relative)
    before = sha(original) if original.exists() else None
    if original.exists(): shutil.copyfile(original, backup)
    target.write_bytes(data)
    assert before is None or sha(original)==before
    return {'before': before, 'after': sha(target), 'source':target.relative_to(ROOT).as_posix(),
        'backup': backup.relative_to(ROOT).as_posix() if before else None}


def source_counter(path, paints=OLD):
    vertices = [None]; paint = None; result = Counter()
    for line in path.open('rb'):
        if line.startswith(b'v '): vertices.append(line[2:].strip())
        elif line.startswith(b'usemtl '): paint=line.split()[1].decode()
        elif line.startswith(b'f ') and paint in paints:
            result[(paint, frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))] += 1
    return result


def patch_canonical(relative, pieces, paints):
    path=ROOT/relative
    counts={b'v':0,b'vt':0,b'vn':0}; dropped=[]; paint=None
    for number,line in enumerate(path.open('rb')):
        head=line.split(maxsplit=1)[0] if line.strip() else b''
        if head in counts: counts[head]+=1
        elif head==b'usemtl': paint=line.split()[1].decode()
        elif head==b'f' and paint in paints: dropped.append(number)
    expected=Counter()
    for old_path,new_path in pieces:
        expected.update(source_counter(old_path,paints))
    assert source_counter(path,paints)==expected and len(dropped)==sum(expected.values())
    tables=[]; tail=[]
    for old_path,new_path in pieces:
        for line in new_path.read_bytes().splitlines(keepends=True):
            head=line.split(maxsplit=1)[0] if line.strip() else b''
            if head in counts: tables.append(line)
            elif head==b'usemtl': tail.append(line)
            elif head==b'f':
                rows=[]
                for token in line.split()[1:]:
                    rows.append(b'/'.join(str(int(index)+counts[kind]).encode() for kind,index in zip(C.KINDS,token.split(b'/'))))
                tail.append(b'f '+b' '.join(rows)+b'\n')
        for kind in counts:
            counts[kind] += sum(line.startswith(kind+b' ') for line in new_path.read_bytes().splitlines())
    target=STAGE/relative;target.parent.mkdir(parents=True,exist_ok=True)
    backup=OUT/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    assert not backup.exists()
    before=sha(path); skip=set(dropped); inserted=False
    with path.open('rb') as incoming,target.open('wb') as updated,backup.open('wb') as original:
        for number,line in enumerate(incoming):
            original.write(line)
            if not inserted and line.startswith(b'usemtl '): updated.writelines(tables);inserted=True
            if number not in skip: updated.write(line)
        updated.writelines(tail)
    assert inserted and sha(path)==before==sha(backup)
    # Prove the entire non-ivy byte stream, including UVs/normals and every
    # unrelated face, survives exactly, without interpreting shared town art.
    with target.open('rb') as stream,path.open('rb') as original:
        table_count=len(tables); start=False
        for number,line in enumerate(original):
            if not start and line.startswith(b'usemtl '):
                for expected_line in tables: assert next(stream)==expected_line
                start=True
            if number not in skip: assert next(stream)==line
        assert stream.read()==b''.join(tail)
    return {'before':before,'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
        'backup':backup.relative_to(ROOT).as_posix(),'removed_ivy_triangles':len(dropped),
        'non_ivy_source_bytes_preserved':True}


def main():
    global OUT, STAGE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refine',action='store_true',help='Refine the already-imported v1 using its archived clearance rectangles.')
    args=parser.parse_args()
    archived=OUT/'before'
    if args.refine:
        OUT=ROOT/'output/belltower/ivy-3d-v1/refined'
        STAGE=OUT/'stage'
    assert not (STAGE/'manifest.json').exists(), 'Choose a new revision instead of replacing evidence.'
    STAGE.mkdir(parents=True,exist_ok=True)
    manifest={'revision':'branching-ivy-3d-v1','files':{},'models':{},
        'scene_sha256_at_stage':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
        'scene_not_modified':True,'collision_not_modified':True,'new_scene_objects':0,
        'source_sha256':{str(p):sha(ROOT/p) for p in [Path('Tools/belltower_ivy.py'),Path('Tools/belltower_stage_ivy.py')]}}
    groups={}; stats=[]
    for kind in ('ivy_climb','ivy_hang'):
        source_root=archived if args.refine else ROOT
        original=next((source_root/'Assets/models/maps/belltower/compiler-safe/west').glob('*_'+kind+'.obj'))
        model=K.Model()
        patch_list=patches(original)
        for points,normal in patch_list:
            stats.append({'kind':kind,'centre':np.mean(points,axis=0).tolist(),
                **I.build(model,points,normal,hanging=kind=='ivy_hang')})
        assert not model.boxes and not model.hulls and not model.props
        groups[kind]=model
    assert len(stats)==25
    manifest['patches_per_half']=stats
    for side in ('west','east'):
        pieces=[]; total=0
        for kind,model in groups.items():
            if side=='east': model=model.mirrored()
            original=next((ROOT/f'Assets/models/maps/belltower/compiler-safe/{side}').glob('*_'+kind+'.obj'))
            piece=OUT/'pieces'/f'{side}-{kind}.obj';piece.parent.mkdir(parents=True,exist_ok=True)
            K.write_obj(piece,model,'belltower_'+side)
            # Reject collapsed exported triangles before the native importer
            # sees them. This uses the actual three-decimal OBJ positions.
            exported = [None]
            for line in piece.read_text().splitlines():
                if line.startswith('v '): exported.append(np.array(list(map(float,line.split()[1:]))))
                elif line.startswith('f '):
                    a,b,c = [exported[int(token.split('/')[0])] for token in line.split()[1:]]
                    assert np.linalg.norm(np.cross(b-a,c-a)) > 1e-8, (side,kind,'Collapsed export triangle')
            assert model.triangle_count()<100000, 'Retain the bounded-import limit.'
            pieces.append((original,piece));total+=model.triangle_count()
            raw=piece.read_bytes();raw=re.sub(rb'^mtllib .*$',b'mtllib materials.mtl',raw,count=1,flags=re.M)
            # Compact only these small isolated ivy imports.
            uncompact=OUT/'pieces'/f'{side}-{kind}-raw.obj';uncompact.write_bytes(raw)
            compact=OUT/'pieces'/f'{side}-{kind}-compact.obj'
            C.compact(uncompact,compact,deduplicate=True)
            relative=original.relative_to(ROOT).as_posix()
            manifest['files'][relative]=stage_file(relative,compact.read_bytes())
        relative=f'Assets/models/maps/belltower/belltower_{side}.obj'
        manifest['files'][relative]=patch_canonical(relative,pieces,set(I.MATERIALS) if args.refine else OLD)
        entries=''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n' for p in I.MATERIALS).encode()
        for relative in (f'Assets/models/maps/belltower/belltower_{side}.mtl',
            f'Assets/models/maps/belltower/compiler-safe/{side}/materials.mtl'):
            original=(ROOT/relative).read_bytes()
            assert all((('newmtl '+p+'\n').encode() in original)==args.refine for p in I.MATERIALS)
            manifest['files'][relative]=stage_file(relative,original if args.refine else original+entries)
        relative=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        original=(ROOT/relative).read_bytes()
        anchor=next(l for l in original.splitlines(keepends=True) if b'from = "ivy_climb.vmat"' in l)
        indent=anchor[:len(anchor)-len(anchor.lstrip())]
        remaps=b''.join(indent+f'{{ from = "{paint}.vmat" to = "{path}" }},\n'.encode() for paint,path in I.MATERIALS.items())
        updated=original if args.refine else original.replace(anchor,remaps+anchor)
        assert (remaps in original) if args.refine else updated.replace(remaps,b'',1)==original
        manifest['files'][relative]=stage_file(relative,updated)
        manifest['models'][side]={'patches':25,'new_ivy_triangles':total,
            'all_non_ivy_obj_bytes_preserved':True,'vmdl_only_two_material_remaps_added':True,
            'collision_blocks_and_bounded_import_list_exact':True}
    texture=ROOT/'Sources/Belltower/ivy/leaf-atlas-v1.png'
    material=('// Branching ivy; original generated atlas: Sources/Belltower/ivy/generation-v1.json\n'
        '"Layer0"\n{\n    shader "shaders/belltower_plants.shader"\n'
        f'    TexturePlants "{I.ATLAS}"\n    F_ALPHA_TEST "1"\n'
        '    g_flAlphaTestReference "0.4"\n    g_flAntiAliasedEdgeStrength "1"\n}\n')
    for relative,data in [('Assets/'+I.ATLAS,texture.read_bytes()),
        ('Assets/'+I.MATERIALS[I.LEAF],material.encode())]:
        manifest['files'][relative]=stage_file(relative,data)
    manifest['source_sha256']['Sources/Belltower/ivy/leaf-atlas-v1.png']=sha(texture)
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(manifest['files']),'patches':50,
        'leaves':2*sum(p['leaves'] for p in stats),'triangles_per_half':total,
        'scene_unchanged':True,'collision_unchanged':True,'other_town_art_preserved':True}))


if __name__=='__main__': main()
