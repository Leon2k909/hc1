"""Audit the fixed-exposure native coverage study without promoting its assets."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / 'output/belltower/quality'
TRIAL = QUALITY / 'forest-coverage-v1'
VIEWS = {
    # Rectangles are (left, top, right, bottom) in the original 1920x1080 captures.
    'valley': {'sky': (650, 40, 1400, 190), 'forest': (750, 345, 1200, 450)},
    'west-ridge': {'sky': (600, 30, 1250, 140), 'forest': (900, 410, 1100, 438)},
    'west-ridge-detail': {'sky': (530, 50, 800, 140), 'forest': (1000, 150, 1300, 260)},
    'terrace': {'sky': (1000, 30, 1500, 200), 'forest': (963, 442, 1050, 495)},
}
SHARED = ('Capture', 'Projection', 'Lighting', 'NativeExposureAfterRender',
          'MainPostprocessSynced', 'SourceScene', 'SourceSceneSha256',
          'CaptureHelperSha256', 'TrialLook')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def image_array(path):
    with Image.open(path) as image:
        assert image.size == (1920, 1080), path
        return np.asarray(image.convert('RGB'), dtype=np.float64)


def region_metrics(before, after, rectangle):
    x0, y0, x1, y1 = rectangle
    a, b = [image[y0:y1, x0:x1] for image in (before, after)]
    difference = np.abs(a - b)
    luminance = [image @ np.array([.2126, .7152, .0722]) for image in (a, b)]
    edge_energy = [float(np.mean(np.abs(np.diff(image, axis=0))) +
                         np.mean(np.abs(np.diff(image, axis=1)))) for image in luminance]
    return dict(rectangle=list(rectangle), mean_abs_rgb_8bit=float(difference.mean()),
                changed_over_3_fraction=float(np.any(difference > 3, axis=2).mean()),
                before_mean_rgb=a.mean(axis=(0, 1)).tolist(),
                after_mean_rgb=b.mean(axis=(0, 1)).tolist(),
                edge_energy_proxy_before=edge_energy[0], edge_energy_proxy_after=edge_energy[1])


def capture(directory, view, manifest_sha, strength=None):
    folder = QUALITY / directory
    metadata = read(folder / f'{view}-camera.json')
    assert metadata['GamePreserved'] and metadata['SelectedDocumentPreserved']
    assert not metadata['SceneHasUnsavedChanges']
    assert all(volume['TexturesValid'] for volume in metadata['Lighting'])
    assert metadata['TrialLook'] == dict(minimum_exposure=2.0, maximum_exposure=2.0,
                                       compensation=0, mode='ACES')
    exposure = metadata['NativeExposureAfterRender']
    assert exposure['MinExposure'] == exposure['MaxExposure'] == 2
    assert exposure['MainMinimumExposure'] == exposure['MainMaximumExposure'] == 2
    assert read(folder / f'{view}-look-restore.json') == dict(ToneRestored=True)
    assert metadata['CaptureHelperSha256'] == sha(ROOT / 'Sources/Belltower/editor/capture-viewport.cs.txt')
    assert metadata['SourceSceneSha256'] == sha(ROOT / 'Assets/scenes/maps/Belltower/belltower.scene')
    if strength is None:
        assert metadata['TrialForestCoverageSlots'] == 0
        assert metadata['ForestCoverageParameters'] is None
    else:
        parameters = metadata['ForestCoverageParameters']
        assert metadata['TrialForestCoverageSlots'] == 88
        assert parameters['StrengthOverride'] == strength
        assert parameters['ManifestSha256'] == manifest_sha
        assert parameters['EngineCoverageSourceVerified']
        assert read(folder / f'{view}-restore.json') == dict(MaterialsRestored=True, Slots=88)
    image = folder / f'{view}.png'
    return metadata, image, image_array(image)


def main():
    manifest_path = TRIAL / 'manifest.json'
    manifest, manifest_sha = read(manifest_path), sha(manifest_path)
    for path, expected in manifest['source_sha256'].items():
        assert sha(ROOT / path) == expected, f'Accepted input changed: {path}'
    for item in manifest['files']:
        assert sha(ROOT / item['source']) == sha(ROOT / 'Assets' / item['path']) == item['sha256']
    imported = read(TRIAL / 'native-import-result.json')
    compiled = read(TRIAL / 'native-compile-shader.json')
    assert imported['ManifestSha256'] == manifest_sha and imported['SceneObjectsAdded'] == 0
    assert imported['GamePreserved'] and imported['SelectedDocumentPreserved']
    assert compiled['CompilerReportedSuccess'] and compiled['CompiledFileExists']
    assert compiled['SourceSha256'] == sha(ROOT / 'Assets' / compiled['Shader'])
    assert compiled['CompiledFileSha256'] == sha(ROOT / 'Assets' / (compiled['Shader'] + '_c'))
    assert compiled['GamePreserved'] and compiled['SelectedDocumentPreserved']
    material_compile = read(TRIAL / 'asset_compile.json')['structuredContent']
    assert material_compile['Success']
    assert material_compile['Path'] == 'materials/belltower/forest/trials/forest_coverage_v1.vmat'
    scene_text = (ROOT / 'Assets/scenes/maps/Belltower/belltower.scene').read_text(encoding='utf-8')
    assert 'forest_coverage_v1.vmat' not in scene_text
    views = []
    for view, regions in VIEWS.items():
        base, base_path, base_pixels = capture('forest-coverage-v1-native-fixed-baseline', view, manifest_sha)
        variants = {}
        for label, strength in (('control', 1), ('half', .5), ('zero', 0)):
            candidate, candidate_path, pixels = capture(f'forest-coverage-v1-native-fixed-{label}', view, manifest_sha, strength)
            assert all(base[key] == candidate[key] for key in SHARED), f'Unmatched settings: {view}/{label}'
            metrics = {name: region_metrics(base_pixels, pixels, rectangle) for name, rectangle in regions.items()}
            if label == 'control':
                assert metrics['sky']['mean_abs_rgb_8bit'] < .1, f'Exposure control failed: {view}'
                assert metrics['forest']['mean_abs_rgb_8bit'] < .1, f'Forest control failed: {view}'
            variants[label] = dict(strength=strength, image=relative(candidate_path), sha256=sha(candidate_path),
                                   matched_recorded_inputs=True, temporary_slots_restored=88,
                                   tone_restored=True, regions=metrics)
        views.append(dict(view=view, baseline_image=relative(base_path), baseline_sha256=sha(base_path), variants=variants))
    helpers = {path: sha(ROOT / path) for path in (
        'Sources/Belltower/editor/capture-viewport.cs.txt',
        'Sources/Belltower/editor/import-forest-coverage-trial.cs.txt',
        'Sources/Belltower/editor/compile-detail-shader.cs.txt')}
    static = read(TRIAL / 'helper-static-compile.json')
    result = dict(
        status='Four fixed-exposure native still comparisons reviewed; trial remains unreferenced.',
        manifest_sha256=manifest_sha, native_shader_compilation_verified=True,
        native_material_compilation_verified=True, installed_unreferenced_assets=[item['path'] for item in manifest['files']],
        current_helper_sha256=helpers,
        static_binding_proof=dict(path=relative(TRIAL / 'helper-static-compile.json'),
                                  current_source_matches={path: static['source_sha256'].get(path) == digest for path, digest in helpers.items()},
                                  scope='Historical static API binding proof. Current helpers also executed successfully in the engine.'),
        views=views, fixed_exposure_control_passed=True,
        exposure_scope='Temporary native QA exposure of 2 with ACES, restored after each capture. Saved automatic exposure is unchanged.',
        invalid_adaptive_comparisons=dict(
            directories=[f'forest-coverage-v1-native-{suffix}' for suffix in ('baseline', 'control', 'half', 'zero')],
            reason='The strength-one control changed the sky and static scenery brightness. Matching exposure settings did not mean matching adapted exposure.'),
        visual_review=dict(
            preferred_experimental_strength=0,
            valley='Lower coarse grey grain; existing distance fade retained, with no new abrupt boundary in this still.',
            ridge='Crown shapes remain visible in the detail view. The regular repeated crown pattern remains conspicuous.',
            terrace='The distant slope is less stippled. The existing tree rows and terrain treatment remain visible.',
            half='Less pronounced change; retains more of the distant coarse pattern.',
            scope='Visual judgement of native fixed-camera stills only. Edge-energy values describe local image changes, not a quality score.'),
        remaining=['Representative native motion and mip-transition review.',
                   'Consistent Belltower gameplay performance before acceptance.',
                   'Further distribution/shape work: alpha compensation alone does not meet the broad visual target.'],
        accepted_scene_changed=False, accepted_shader_changed=False, source_pixels_changed=False,
        trial_promoted=False, gameplay_performance_verified=False, overall_quality_goal_complete=False)
    target = TRIAL / 'native-fixed-review.json'
    target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(report=relative(target), fixed_control_views=len(views),
                          controls_passed=True, temporary_slots_restored_per_trial_capture=88,
                          preferred_experimental_strength=0, trial_promoted=False)))


if __name__ == '__main__':
    main()
