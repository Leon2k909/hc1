"""Audit the native decal stills and projector placement without saving the map."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / 'output/belltower/quality'
STAGE = QUALITY / 'ground-edge-v2'
VIEWS = ('ground-edge', 'ground-edge-close', 'ground-edge-sunlit', 'ground-edge-sunlit-close',
         'ground-edge-east-street', 'ground-edge-east-street-close', 'ground-edge-east-wall', 'ground-edge-east-wall-close')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def relative(path):
    return path.relative_to(ROOT).as_posix()


def pixels(path):
    with Image.open(path) as image:
        assert image.size == (1920, 1080)
        return np.asarray(image.convert('RGB'), dtype=np.int16)


def difference(before, after):
    delta = np.abs(before - after)
    return dict(mean_abs_rgb_8bit=float(delta.mean()), changed_over_3_fraction=float(np.any(delta > 3, axis=2).mean()))


def main():
    manifest_path = STAGE / 'manifest.json'
    manifest, manifest_sha = read(manifest_path), sha(manifest_path)
    for path, expected in manifest['source_sha256'].items():
        assert sha(ROOT / path) == expected, path
    for item in manifest['files']:
        assert sha(ROOT / item['source']) == sha(ROOT / 'Assets' / item['path']) == item['sha256']
    imported = read(STAGE / 'native-import-result.json')
    assert imported['ManifestSha256'] == manifest_sha and imported['Imported'] == 4
    assert imported['GamePreserved'] and imported['SelectedDocumentPreserved'] and not imported['SceneSaved']
    compilers = []
    for index, item in enumerate(manifest['files']):
        compiled = read(STAGE / f'compile-{index}/asset_compile.json')['structuredContent']
        assert compiled['Success'] and compiled['Path'] == item['path']
        compilers.append(dict(path=item['path'], source_sha256=item['sha256'],
                              compiled_sha256=sha(ROOT / 'Assets' / (item['path'] + '_c'))))
    audit = read(STAGE / 'native-projection-bounds.json')
    assert audit['ManifestSha256'] == manifest_sha and audit['Placements'] == audit['SurfacePlaneContained'] == 116
    assert not audit['Errors'] and audit['MaximumPlanarErrorInches'] < .05
    assert audit['OriginalObjectIdentitiesRestored'] and not audit['SceneHasUnsavedChanges']
    assert audit['GamePreserved'] and audit['SelectedDocumentPreserved']
    scene = ROOT / 'Assets/scenes/maps/Belltower/belltower.scene'
    assert 'ground-edge-v2' not in scene.read_text(encoding='utf-8')
    shared = ('Camera', 'NativeExposure', 'LoadedDefinitions', 'ManifestSha256', 'SourceSceneSha256', 'HelperSha256')
    reviewed = []
    for view in VIEWS:
        metadata, images = {}, {}
        east = '-east-' in view
        for label, directory, count in (
                ('baseline', 'ground-edge-v2-native-east-baseline' if east else 'ground-edge-v2-native-dedup-baseline', 0),
                ('control', 'ground-edge-v2-native-east-control' if east else 'ground-edge-v2-native-all-control', 116),
                ('candidate', 'ground-edge-v2-native-east-half' if east else 'ground-edge-v2-native-all-half', 116)):
            folder = QUALITY / directory
            entry = read(folder / f'{view}-camera.json')
            restored = read(folder / f'{view}-restore.json')
            assert entry['ManifestSha256'] == manifest_sha and entry['SourceSceneSha256'] == sha(scene)
            assert entry['HelperSha256'] == sha(ROOT / 'Sources/Belltower/editor/capture-ground-decals.cs.txt')
            assert entry['GamePreserved'] and entry['SelectedDocumentPreserved'] and not entry['SceneHasUnsavedChanges']
            assert entry['TrialDecals'] == count
            assert restored == dict(ObjectsRestored=True, ToneRestored=True, DecalsRemoved=count)
            assert entry['NativeExposure'] == dict(MinExposure=2, MaxExposure=2, Compensation=0)
            assert all(not definition['NormalOverride'] and not definition['RmoOverride'] for definition in entry['LoadedDefinitions'])
            metadata[label] = entry
            images[label] = folder / f'{view}.png'
        assert all(metadata['baseline'][key] == metadata[label][key] for key in shared for label in ('control', 'candidate'))
        assert metadata['control']['ColorMix'] == 0 and metadata['candidate']['ColorMix'] == .5
        arrays = {label: pixels(path) for label, path in images.items()}
        control = difference(arrays['baseline'], arrays['control'])
        candidate = difference(arrays['baseline'], arrays['candidate'])
        assert control['mean_abs_rgb_8bit'] < .1, f'Control changed the image: {view}'
        assert candidate['changed_over_3_fraction'] > .00001, f'No visible decal change: {view}'
        reviewed.append(dict(view=view, images={label: dict(path=relative(path), sha256=sha(path)) for label, path in images.items()},
                             control=control, candidate=candidate, recorded_inputs_matched=True,
                             decals_restored_per_trial_capture=116, tone_restored=True))
    report = dict(status='Native albedo-only decal candidate reviewed in eight stills across both halves; map unchanged.',
                  manifest_sha256=manifest_sha, compilation=compilers, native_projection_audit=audit, views=reviewed,
                  native_control_passed=True, candidate_color_mix=.5,
                  method='Native Multiply decal, no normal, roughness, metalness, AO, emission or parallax override.',
                  original_source_pixels_and_alpha_preserved=True,
                  visual_review='The existing cobble relief remains visible through a restrained dirt stain in sun and shade. The earlier bright flat gravel strip is avoided. This is a local still-image improvement, not overall map acceptance.',
                  invalid_captures=dict(directories=['ground-edge-v2-native-baseline', 'ground-edge-v2-native-control',
                                                    'ground-edge-v2-native-half', 'ground-edge-v2-native-warm-baseline',
                                                    'ground-edge-v2-native-warm-control', 'ground-edge-v2-native-warm-half'],
                                        reason='Background stone/plaster textures lost detail with the initial material prewarm. The current helper uses the established filtered material set, keeps distinct materials through prewarm, and requests all normal-map variants.'),
                  exposure_scope='Temporary ACES exposure 2 for comparisons; original tone and camera restored after each image.',
                  remaining=['Check representative gameplay motion, distance/culling and cost in Belltower when the shared editor is available.',
                             'Check the remaining frontages during that walkthrough before saving a permanent scene group.'],
                  accepted_scene_changed=False, trial_promoted=False, gameplay_performance_verified=False,
                  overall_quality_goal_complete=False)
    path = STAGE / 'native-review.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(report=relative(path), native_control_views=len(VIEWS), checked_native_placements=116,
                          max_planar_error_inches=audit['MaximumPlanarErrorInches'], all_restored=True, promoted=False)))


if __name__ == '__main__':
    main()
