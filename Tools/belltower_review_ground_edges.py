"""Record a reviewed, matched offline comparison; never grants native acceptance."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

import belltower_ground_edges as G


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-note', required=True)
    args = parser.parse_args()
    manifest_path = G.STAGE / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    checks = json.loads((G.STAGE / 'geometry-checks.json').read_text(encoding='utf-8'))
    assert checks['passed'] and checks['manifest_sha256'] == G.sha(manifest_path)
    assert checks['checker_sha256'] == G.sha(G.ROOT / 'Tools/belltower_check_ground_edges.py')
    for relative, expected in manifest['source_sha256'].items():
        assert G.sha(G.ROOT / relative) == expected, relative
    entries = {entry['name']: entry for entry in json.loads((G.STUDIO / 'models.json').read_text(encoding='utf-8'))}
    views = {}
    for suffix in ('', '-close'):
        captures, pixels = [], []
        for state in ('before', 'after'):
            name = 'ground-edge-' + state + suffix
            entry = entries[name]
            data = json.loads((G.STUDIO / (name + '-render.json')).read_text(encoding='utf-8'))
            assert data['model_sha256'] == G.sha(G.STUDIO / (name + '.obj'))
            assert data['image_sha256'] == G.sha(G.STUDIO / (name + '.png'))
            assert data['preview_source_sha256'] == G.sha(G.ROOT / 'Tools/belltower_garden_preview.py')
            bounds = np.asarray(entry['review_bounds']) * .0254
            expected_position = bounds.mean(axis=0) + np.asarray(entry['camera_offset']) * np.max(bounds[1] - bounds[0])
            assert np.allclose(data['camera_position'], expected_position, atol=1e-5), 'Stale camera metadata'
            assert np.allclose(data['review_bounds'], bounds, atol=1e-6)
            assert data['device'] == 'CPU' and data['threads'] == 2
            with Image.open(G.STUDIO / (name + '.png')) as image:
                assert list(image.size) == data['size']
                pixels.append(np.asarray(image.convert('RGB'), dtype=np.int16))
            captures.append(data)
        for key in ('camera_position', 'camera_rotation', 'lens', 'review_bounds', 'exposure', 'view_transform', 'size', 'samples', 'engine'):
            assert captures[0][key] == captures[1][key], key
        delta = np.abs(pixels[1] - pixels[0])
        fraction = float(np.mean(np.max(delta, axis=2) > 12))
        assert fraction > .0001, 'The detail is absent from the matched comparison'
        views[suffix or 'wide'] = dict(before_image='output/belltower/quality/ground-edge-v1-studio/ground-edge-before' + suffix + '.png',
                                      after_image='output/belltower/quality/ground-edge-v1-studio/ground-edge-after' + suffix + '.png',
                                      matched_camera_lighting_and_exposure=True,
                                      before_sha256=captures[0]['image_sha256'], after_sha256=captures[1]['image_sha256'],
                                      changed_pixels_over_12_fraction=fraction,
                                      exposure=captures[1]['exposure'])
    result = dict(revision='ground-edge-v1', status='offline construction comparison reviewed; native validation pending',
                  review_note=args.review_note, source_atlas=G.SOURCE.relative_to(G.ROOT).as_posix(),
                  source_atlas_sha256=G.sha(G.SOURCE),
                  prompt_and_provenance=G.SOURCE.with_suffix('.json').relative_to(G.ROOT).as_posix(),
                  image_method='built-in image_gen edit; original pixels and alpha preserved',
                  stage_manifest='output/belltower/quality/ground-edge-v1/manifest.json',
                  stage_manifest_sha256=G.sha(manifest_path), geometry_checks=checks,
                  views=views, native_verified=False, scene_or_collision_changes=False,
                  trial_assets_currently_installed=sum((G.ROOT / 'Assets' / record['path']).exists() for record in manifest['files']),
                  import_helper='Sources/Belltower/editor/import-ground-edge-trial.cs.txt',
                  import_helper_sha256=G.sha(G.ROOT / 'Sources/Belltower/editor/import-ground-edge-trial.cs.txt'),
                  remaining=['Compile the new shader, material and two models in a coordinated editor window.',
                             'Compare current Belltower street views with temporary trial geometry, restoring scene and play state.',
                             'Check alpha edges, paving contact, distance fade and gameplay frame times before saving any scene change.'])
    target = G.ROOT / 'Sources/Belltower/ground-edges/trial-v1.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    for output in (target, G.STAGE / 'offline-review.json'):
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(record=target.relative_to(G.ROOT).as_posix(), views=len(views), native_verified=False)))


if __name__ == '__main__':
    main()
