"""Stage a refinement of the installed shop cloth, preserving all other meshes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import map_kit as K
import belltower_map as B
from belltower_stage_shop_awning_cloth import ROOT, OUT, LEGACY, current_hook, models, patch, point, sha


def obj_keys(path):
    vertices, wanted, paint = [], Counter(), None
    for line in path.open('rb'):
        if line.startswith(b'v '): vertices.append(point(line[2:].decode()))
        elif line.startswith(b'usemtl '): paint = line.split()[1]
        elif line.startswith(b'f '):
            face = [vertices[int(token.split(b'/')[0])-1] for token in line.split()[1:]]
            assert len(face) == 3
            wanted[paint, frozenset(face)] += 1
    return wanted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args(); assert re.fullmatch(r'[a-z0-9-]+', args.revision)
    stage = OUT/args.revision/'stage'; assert not (stage/'manifest.json').exists()
    stage.mkdir(parents=True, exist_ok=True)
    _, new, placements = models()
    report = {'revision': 'shop-awning-cloth-v1', 'stage_revision': args.revision, 'files': {},
              'awnings_per_half': len(placements), 'placements_west': placements,
              'new_triangles_per_half': new.triangle_count(), 'source_sha256': {},
              'protected_sha256': {}, 'map_awning_hook': current_hook(), 'models': {}}
    for relative in ['Tools/belltower_shop_awning_cloth.py', 'Tools/belltower_stage_shop_awning_cloth.py',
                     'Tools/belltower_refresh_shop_awning_cloth.py', LEGACY.relative_to(ROOT).as_posix()]:
        report['source_sha256'][relative] = sha(ROOT/relative)
    inputs = {}
    for side in ['west', 'east']:
        candidate = new if side == 'west' else new.mirrored(B.EAST_PAINTS)
        candidate.tile_overrides.update({paint: 48. for paint in candidate.polygons})
        own = ROOT/f'Assets/models/maps/belltower/shop-awning-cloth-v1/{side}.obj'
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        inputs.update({p: sha(p) for p in [own, canonical]})
        wanted = obj_keys(own)
        piece = stage/own.relative_to(ROOT)
        piece.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(piece, candidate, f'belltower_{side}')
        # Existing material imports remain byte-for-byte identical.
        assert sha(piece.with_suffix('.mtl')) == sha(own.with_suffix('.mtl'))
        piece.with_suffix('.mtl').unlink()
        row = patch(canonical, stage/canonical.relative_to(ROOT), wanted, piece)
        assert row['found'] == wanted, ('Current cloth differs', side, wanted-row['found'])
        report['models'][side] = {'previous_cloth_triangles_removed': row['removed'],
                                 'unrelated_obj_bytes_exact': True,
                                 'unrelated_obj_bytes_sha256': row['unrelated_bytes_sha256']}
        vmdl = canonical.with_suffix('.vmdl')
        assert vmdl.read_bytes().count(f'filename = "models/maps/belltower/shop-awning-cloth-v1/{side}.obj"'.encode()) == 1
        for protected in [vmdl, canonical.with_suffix('.mtl'), own.with_suffix('.mtl')]:
            report['protected_sha256'][protected.relative_to(ROOT).as_posix()] = sha(protected)
    for target, digest in inputs.items(): assert sha(target) == digest, ('Concurrent resource change', target)
    for source in (stage/'Assets').rglob('*.obj'):
        relative = source.relative_to(stage); target = ROOT/relative
        backup = stage/'before'/relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, backup)
        assert sha(backup) == inputs[target]
        report['files'][relative.as_posix()] = {'source': source.relative_to(ROOT).as_posix(),
            'backup': backup.relative_to(ROOT).as_posix(), 'before': inputs[target], 'after': sha(source)}
    (stage/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'awnings': len(placements)*2, 'triangles_per_half': new.triangle_count(),
                      'targets': len(report['files']), 'stage': str(stage)}))


if __name__ == '__main__': main()
