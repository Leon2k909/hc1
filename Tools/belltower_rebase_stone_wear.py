"""Rebase only shared authoring OBJs; retain all bounded imports and guards."""
import argparse
import copy
import json
import re
import shutil
import subprocess
import sys

import belltower_stage_stone_wear as S


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--import-native', action='store_true')
    args = parser.parse_args()
    for name in (args.stage, args.target):
        assert re.fullmatch('[a-z0-9-]+', name), name
    original = json.loads((S.OUT/args.stage/'manifest.json').read_text())
    manifest = copy.deepcopy(original)
    destination = S.OUT/args.target
    assert not destination.exists(), 'Preserve each rebase.'
    destination.mkdir()
    for group in ('source_sha256', 'protected_sha256'):
        for relative, digest in manifest[group].items():
            assert S.sha(S.ROOT/relative) == digest, ('Shared input changed', relative)
    changed = []
    for relative, item in manifest['files'].items():
        actual = S.sha(S.ROOT/relative) if (S.ROOT/relative).exists() else None
        if actual == item['before']:
            continue
        assert re.fullmatch(r'Assets/models/maps/belltower/belltower_(west|east|centre)\.obj', relative), ('Non-authoring target changed', relative)
        changed.append(relative)
    assert changed, 'No authoring rebase needed.'
    history = []
    for relative in changed:
        side = re.search(r'belltower_(\w+)\.obj$', relative).group(1)
        before = S.sha(S.ROOT/relative)
        old, _ = S.fixtures(side == 'centre')
        if side == 'east':
            old = old.mirrored(S.B.EAST_PAINTS)
        lookup, faces = S.polygons(old)
        leaf = f'Assets/models/maps/belltower/edge-realism-v1/{side}.obj'
        piece = S.ROOT/manifest['files'][leaf]['source']
        target = destination/relative
        result, found = S.patch(S.ROOT/relative, target, lookup, piece)
        S.coverage(found, lookup, faces)
        assert result['removed_triangles'] == manifest['models'][side]['removed_triangles']
        backup = destination/'before'/relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(S.ROOT/relative, backup)
        assert S.sha(backup) == before == S.sha(S.ROOT/relative)
        manifest['files'][relative] = {
            'before': before, 'after': S.sha(target),
            'source': target.relative_to(S.ROOT).as_posix(),
            'backup': backup.relative_to(S.ROOT).as_posix(),
        }
        manifest['models'][side].update(result)
        history.append({'path': relative, 'previous_before': original['files'][relative]['before'], 'rebased_before': before, **result})
    manifest['rebase'] = {'from': args.stage, 'authoring_files': history}
    manifest['source_sha256']['Tools/belltower_rebase_stone_wear.py'] = S.sha(S.ROOT/'Tools/belltower_rebase_stone_wear.py')
    for relative, item in manifest['files'].items():
        assert S.sha(S.ROOT/item['source']) == item['after'], relative
        actual = S.sha(S.ROOT/relative) if (S.ROOT/relative).exists() else None
        assert actual == item['before'], ('Shared target changed again', relative)
        if item['backup']:
            assert S.sha(S.ROOT/item['backup']) == item['before']
    for group in ('source_sha256', 'protected_sha256'):
        for relative, digest in manifest[group].items():
            assert S.sha(S.ROOT/relative) == digest, relative
    (destination/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'rebased': history, 'stage': args.target}), flush=True)
    if args.import_native:
        (S.OUT/'import-request.json').write_text(json.dumps({'stage': args.target})+'\n')
        subprocess.run(['rtk', 'proxy', sys.executable, '-X', 'utf8', 'output/knife-throw/editor_check.py',
                        '--script', 'Sources/Belltower/editor/import-stone-wear-v1.cs.txt',
                        '--output-dir', f'output/belltower/edge-realism-v1/import-{args.target}',
                        '--timeout', '60', '--direct-call', '--cleanup-exchange'], cwd=S.ROOT, check=True)


if __name__ == '__main__':
    main()
