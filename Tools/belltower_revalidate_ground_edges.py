"""Refresh provenance only when current inputs regenerate identical trial assets."""
import copy
import json
from pathlib import Path
import shutil

import belltower_ground_edges as G


def main():
    stage = G.STAGE
    old_path = stage / 'manifest.json'
    old = json.loads(old_path.read_text(encoding='utf-8'))
    old_sha = G.sha(old_path)
    changed = {path: dict(before=digest, after=G.sha(G.ROOT / path))
               for path, digest in old['source_sha256'].items() if G.sha(G.ROOT / path) != digest}
    if not changed:
        print(json.dumps(dict(status='All recorded inputs are current; no update required.')))
        return
    assert set(changed) == {'Tools/belltower_map.py'}, changed
    inputs_before = {path: G.sha(G.ROOT / path) for path in old['source_sha256']}
    # Regenerate in a separate output directory; never write live project assets.
    candidate = G.QUALITY / 'ground-edge-v1-revalidation-candidate'
    G.STAGE, G.STUDIO = candidate, candidate / 'studio'
    G.main()
    fresh = json.loads((candidate / 'manifest.json').read_text(encoding='utf-8'))
    assert inputs_before == {path: G.sha(G.ROOT / path) for path in inputs_before}, 'Inputs changed during regeneration'
    assert fresh['source_sha256'] == inputs_before
    old_files = {item['path']: item for item in old['files']}
    assert set(old_files) == {item['path'] for item in fresh['files']}
    for item in fresh['files']:
        previous = old_files[item['path']]
        assert item['sha256'] == previous['sha256']
        assert G.sha(G.ROOT / item['source']) == G.sha(G.ROOT / previous['source']) == item['sha256']
        assert G.sha(G.ROOT / 'Assets' / item['path']) == item['sha256']
    normalized = copy.deepcopy(fresh)
    for item in normalized['files']:
        item['source'] = old_files[item['path']]['source']
    expected = copy.deepcopy(old)
    expected['source_sha256'] = inputs_before
    assert normalized == expected, 'A placement, asset or other manifest property changed'
    archive = stage / ('provenance-' + old_sha[:12])
    archive.mkdir(exist_ok=True)
    archived = []
    for name in ('manifest.json', 'geometry-checks.json', 'native-import-result.json'):
        source, target = stage / name, archive / name
        if target.exists():
            assert G.sha(target) == G.sha(source), f'An existing provenance archive differs: {name}'
        else:
            shutil.copy2(source, target)
        archived.append(target.relative_to(G.ROOT).as_posix())
    assert G.sha(old_path) == old_sha, 'Original manifest changed during validation'
    assert inputs_before == {path: G.sha(G.ROOT / path) for path in inputs_before}
    old_path.write_text(json.dumps(normalized, indent=2) + '\n', encoding='utf-8')
    result = dict(status='Provenance refreshed after byte-identical regeneration.',
                  previous_manifest_sha256=old_sha, manifest_sha256=G.sha(old_path),
                  source_drift=changed, archived_provenance=archived,
                  regenerated_trial_files_identical=len(fresh['files']),
                  frontages_identical=True, placements_identical=True,
                  accepted_assets_written=False, trial_assets_written=False,
                  native_revalidation_required=True)
    (stage / 'source-revalidation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
