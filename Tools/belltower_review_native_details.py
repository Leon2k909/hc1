"""Record the reviewed native comparisons without promoting either trial."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality'
SHARED = ('Capture', 'Projection', 'Lighting', 'NativeExposureAfterRender',
          'MainPostprocessSynced', 'SourceScene', 'SourceSceneSha256', 'CaptureHelperSha256')


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair(before, after, view, slots=0, models=0):
    a = read(f'output/belltower/quality/{before}/{view}-camera.json')
    b = read(f'output/belltower/quality/{after}/{view}-camera.json')
    assert all(a[key] == b[key] for key in SHARED), f'Unmatched capture inputs: {view}'
    assert a['SourceSceneSha256'] == sha(ROOT / 'Assets/scenes/maps/Belltower/belltower.scene')
    for capture in (a, b):
        assert capture['GamePreserved'] and capture['SelectedDocumentPreserved']
        assert not capture['SceneHasUnsavedChanges']
        assert all(volume['TexturesValid'] for volume in capture['Lighting'])
    assert b['TrialForestDetailSlots'] == slots and b['TrialGroundEdgeModels'] == models
    if slots:
        restoration = read(f'output/belltower/quality/{after}/{view}-restore.json')
        assert restoration == dict(MaterialsRestored=True, Slots=slots)
    if models:
        restoration = read(f'output/belltower/quality/{after}/{view}-ground-edge-restore.json')
        assert restoration == dict(GroundEdgesRestored=True, ModelsRemoved=models)
        if b.get('TrialLook'):
            assert a['TrialLook'] == b['TrialLook']
            for directory in (before, after):
                assert read(f'output/belltower/quality/{directory}/{view}-look-restore.json') == dict(ToneRestored=True)
    paths = [OUT / directory / f'{view}.png' for directory in (before, after)]
    assert all(Image.open(path).size == (1920, 1080) for path in paths)
    return dict(view=view, before=paths[0].relative_to(ROOT).as_posix(), after=paths[1].relative_to(ROOT).as_posix(),
                before_sha256=sha(paths[0]), after_sha256=sha(paths[1]), matched_inputs=True,
                source_scene_sha256=a['SourceSceneSha256'], capture_helper_sha256=a['CaptureHelperSha256'],
                temporary_forest_slots=slots, temporary_ground_models=models, restoration_verified=True)


def regional_difference(before, after):
    a, b = [np.asarray(Image.open(path).convert('RGB'), dtype=np.int16) for path in (before, after)]
    regions = dict(hill=(335, 480, 850, 1160), city=(650, 1000, 200, 1600), sky=(50, 250, 650, 1300))
    result = {}
    for key, (y0, y1, x0, x1) in regions.items():
        difference = np.abs(a[y0:y1, x0:x1] - b[y0:y1, x0:x1])
        result[key] = dict(mean_abs_rgb_8bit=float(difference.mean()),
                           changed_over_3_fraction=float(np.any(difference > 3, axis=2).mean()))
    return result


def main():
    compiler = {revision: read(f'output/belltower/quality/{revision}/native-compile-shader.json')
                for revision in ('forest-detail-v1', 'ground-edge-v1')}
    assets = {}
    for revision, compiled in compiler.items():
        manifest_path = OUT / revision / 'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        imported = read(f'output/belltower/quality/{revision}/native-import-result.json')
        assert imported['ManifestSha256'] == sha(manifest_path)
        assert compiled['CompilerReportedSuccess'] and compiled['CompiledFileExists']
        assert compiled['SourceSha256'] == sha(ROOT / 'Assets' / compiled['Shader'])
        assert compiled['CompiledFileSha256'] == sha(ROOT / 'Assets' / (compiled['Shader'] + '_c'))
        assert compiled['GamePreserved'] and compiled['SelectedDocumentPreserved']
        assets[revision] = [item['path'] for item in manifest['files']]
        assert all(sha(ROOT / 'Assets' / item['path']) == item['sha256'] for item in manifest['files'])
    forest = [pair('forest-detail-v1-native-baseline-current', 'forest-detail-v1-native-candidate', view, slots=88)
              for view in ('west-ridge', 'west-ridge-detail', 'valley', 'terrace')]
    null = [pair('forest-detail-v1-native-baseline-current', 'forest-detail-v1-native-null', view, slots=88)
            for view in ('west-ridge', 'valley')]
    for view in ('west-ridge', 'valley'):
        capture = read(f'output/belltower/quality/forest-detail-v1-native-null/{view}-camera.json')
        assert capture['ForestDetailParameters']['BlendOverride'] == 0
    base = OUT / 'forest-detail-v1-native-baseline-current/west-ridge.png'
    repeated = regional_difference(base, OUT / 'forest-detail-v1-native-baseline-repeat/west-ridge.png')
    zero = regional_difference(base, OUT / 'forest-detail-v1-native-null/west-ridge.png')
    assert zero['hill']['mean_abs_rgb_8bit'] < repeated['hill']['mean_abs_rgb_8bit'] + .05
    assert zero['city']['mean_abs_rgb_8bit'] < .1
    fade = [pair('forest-detail-v1-native-fade-default', 'forest-detail-v1-native-fade-10k22k', view, slots=88)
            for view in ('valley', 'west-ridge-detail')]
    ground = [pair('ground-edge-v1-native-visible-baseline', 'ground-edge-v1-native-visible-candidate', 'ground-edge-close', models=2)]
    ground.append(pair('ground-edge-v1-native-fixed-wide-baseline', 'ground-edge-v1-native-fixed-wide-candidate', 'ground-edge', models=2))
    ground.extend(pair('ground-edge-v1-native-fixed-sunlit-baseline', 'ground-edge-v1-native-fixed-sunlit-candidate', view, models=2)
                  for view in ('ground-edge-sunlit', 'ground-edge-sunlit-close'))
    revalidation = read('output/belltower/quality/ground-edge-v1/source-revalidation.json')
    assert revalidation['regenerated_trial_files_identical'] == 9 and revalidation['placements_identical']
    assert revalidation['manifest_sha256'] == sha(OUT / 'ground-edge-v1/manifest.json')
    original_manifest = read(revalidation['archived_provenance'][0])
    current_manifest = read('output/belltower/quality/ground-edge-v1/manifest.json')
    assert {item['path']: item['sha256'] for item in original_manifest['files']} == {
        item['path']: item['sha256'] for item in current_manifest['files']}
    cleanup = read('output/belltower/quality/ground-edge-v1/runtime-cleanup-audit.json')
    assert not cleanup['OriginalRuntimeSceneStillActive'] and cleanup['EditorComparisonObjectsRemaining'] == 0
    assert cleanup['GamePreserved'] and cleanup['SelectedDocumentPreserved']
    result = dict(
        status='Native comparisons reviewed; neither trial promoted.', installed_unreferenced_assets=assets,
        native_shader_compilation_verified=True, loaded_forest_calibration_verified=True,
        forest_colour=dict(views=forest, blend_zero_controls=null, repeat_baseline_regions=repeated,
                           blend_zero_regions=zero, review='Subtle additional crown colour/detail. Distant woodland still forms a noisy pattern; this does not meet the overall quality goal.'),
        forest_fade=dict(views=fade, tested_range=[10000, 22000], accepted=False,
                         review='Reject: the near ridge exposes a conspicuous boundary between cards and the underlying landscape.'),
        ground_edges=dict(views=ground, accepted=False,
                          review='Reject for saved-map use: shaded close and contextual views are unobstructed, but the new sunlit pair exposes a flat tan gravel strip that bridges the cobble relief. Broken alpha edges alone do not establish convincing contact.',
                          source_revalidation=revalidation,
                          fixed_exposure_scope='New contextual and sunlit comparisons temporarily use ACES exposure 2. Tone and original scene object identities were restored.',
                          invalid_views=[dict(before=f'{before}/{view}.png', after=f'{after}/{view}.png', reason=reason)
                                         for before, after, view, reason in (
                                             ('ground-edge-v1-native-baseline', 'ground-edge-v1-native-candidate', 'ground-edge', 'Market stand obstructs the deposit.'),
                                             ('ground-edge-v1-native-baseline', 'ground-edge-v1-native-candidate', 'ground-edge-close', 'Review camera intersects the market stand.'),
                                             ('ground-edge-v1-native-visible-baseline', 'ground-edge-v1-native-visible-candidate', 'ground-edge', 'Wider eye point intersects a wall.'))],
                          remaining=['Redesign the ground contact treatment before promotion; the current flat albedo mesh fails the sunlit review.',
                                     'Recheck distance fade and gameplay performance after that redesign.']),
        performance=dict(verified=False, reason='The runtime player camera moved, then the shared editor switched from Belltower to Ares. No fair A/B timing was completed.'),
        cleanup=cleanup, accepted_scene_changed=False, gameplay_performance_verified=False, overall_quality_goal_complete=False)
    path = OUT / 'native-detail-review-oct18.json'
    path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(report=path.relative_to(ROOT).as_posix(), forest_pairs=len(forest),
                          blend_zero_controls=len(null), rejected_fade_pairs=len(fade), valid_ground_pairs=len(ground),
                          restoration_verified=True, trials_promoted=False, gameplay_performance_verified=False)))


if __name__ == '__main__':
    main()
