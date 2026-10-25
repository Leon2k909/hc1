"""Stage the reviewed local chips on installed stone meshes, retaining other work."""
from collections import Counter
import argparse
import json
from pathlib import Path
import re
import shutil
import belltower_stage_stone_wear as S
import belltower_stone_chips as Chips


def installed_faces(path):
    positions = {}; faces = []; lookup = {}; paint = None
    for line in path.open('rb'):
        if line.startswith(b'v '): positions[len(positions)+1] = S.point(line[2:].decode())
        elif line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f '):
            vertices = [positions[int(token.split(b'/')[0])] for token in line.split()[1:]]
            assert len(vertices) == 3
            key = (paint, frozenset(vertices))
            assert key not in lookup, ('Duplicate installed stone triangle', key)
            lookup[key] = len(faces); faces.append((paint, vertices))
    return lookup, faces


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',default='props-chips-v8')
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+',args.stage)
    previous = json.loads((S.OUT/'import-request.json').read_text())['stage']
    stage = S.OUT/args.stage
    assert not stage.exists()
    stage.mkdir()
    original = json.loads((S.OUT/'props-rebase-v6/manifest.json').read_text())
    inputs = {relative:S.sha(S.ROOT/relative) for relative in original['source_sha256']}
    for relative in ('Tools/belltower_stone_chips.py', 'Tools/belltower_stage_stone_chips.py'):
        inputs[relative] = S.sha(S.ROOT/relative)
    protected = {relative:S.sha(S.ROOT/relative) for relative in original['protected_sha256']}
    for side in ('west','east','centre'):
        relative = f'Assets/models/maps/belltower/belltower_{side}.vmdl'
        protected[relative] = S.sha(S.ROOT/relative)
    files = {}; models = {}
    def record(relative, path):
        relative = Path(relative).as_posix()
        before = S.sha(S.ROOT/relative)
        backup = stage/'before'/relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(S.ROOT/relative, backup)
        assert before == S.sha(backup)
        files[relative] = {'before':before, 'after':S.sha(path),
                           'source':path.relative_to(S.ROOT).as_posix(),
                           'backup':backup.relative_to(S.ROOT).as_posix()}
    for side in ('west','east','centre'):
        _, model = S.fixtures(side == 'centre')
        if side == 'east': model = model.mirrored(S.B.EAST_PAINTS)
        assert model.triangle_count() < 65000, (side,model.triangle_count())
        leaf = Path(f'Assets/models/maps/belltower/edge-realism-v1/{side}.obj')
        current_leaf = S.ROOT/leaf
        leaf_before = S.sha(current_leaf)
        lookup, faces = installed_faces(current_leaf)
        piece = stage/leaf
        piece.parent.mkdir(parents=True, exist_ok=True)
        S.K.write_obj(piece, model, 'belltower_'+side)
        record(leaf,piece); record(leaf.with_suffix('.mtl'),piece.with_suffix('.mtl'))
        assert files[leaf.as_posix()]['before'] == leaf_before
        canonical = Path(f'Assets/models/maps/belltower/belltower_{side}.obj')
        result, found = S.patch(S.ROOT/canonical,stage/canonical,lookup,piece)
        S.coverage(found,lookup,faces)
        record(canonical,stage/canonical)
        models[side] = {**result,'new_triangles':model.triangle_count(),
                        'new_import':leaf.relative_to('Assets').as_posix(),
                        'all_prior_render_imports_retained':True,'physics_exact':True}
        raw = (S.ROOT/f'Assets/models/maps/belltower/belltower_{side}.vmdl').read_text()
        for paint in model.polygons:
            match = re.search(r'from = "'+re.escape(paint)+r'\.vmat" to = "([^"]+)"',raw)
            assert match and match.group(1) == model.material_overrides[paint], (side,paint)
    report = {'revision':'belltower-stone-wear-v1','replaces_installed_geometry':previous,
              'review':'Local silhouette chips; churchyard tombs retain cut-stone courses.',
              'files':files,'models':models,'source_sha256':inputs,'protected_sha256':protected,
              'scope':original['scope'],'collision_unchanged':True,
              'fountain_ornaments_preserved':True,'water_shaders_and_texture_pixels_unchanged':True,
              'trough_water_recess_inches':2.7,
              'chip_geometry_checks':dict(Chips.CHIP_STATS),
              'max_new_triangles_per_import':max(m['new_triangles'] for m in models.values())}
    (stage/'plan-draft.json').write_text(json.dumps(report,indent=2)+'\n')
    for group in (inputs,protected):
        for relative,digest in group.items(): assert S.sha(S.ROOT/relative) == digest, relative
    for relative,item in files.items():
        assert S.sha(S.ROOT/relative) == item['before'], ('Shared target changed',relative)
        assert S.sha(S.ROOT/item['source']) == item['after']
    (stage/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    receipt = S.OUT/('native-import-'+previous+'.json')
    if not receipt.exists(): receipt.write_bytes((S.OUT/'native-import.json').read_bytes())
    (S.OUT/'import-request.json').write_text(json.dumps({'stage':stage.name})+'\n')
    print(json.dumps({'stage':stage.name,'models':models,'files':len(files)}),flush=True)


if __name__ == '__main__': main()
