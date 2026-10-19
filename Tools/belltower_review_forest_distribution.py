"""Record the bounded native density comparison and its visual rejection."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / 'output/belltower/quality'
STAGE = QUALITY / 'forest-distribution-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def pixels(path):
    with Image.open(path) as image:
        assert image.size == (1920, 1080)
        return np.asarray(image.convert('RGB'), dtype=np.int16)


def main():
    manifest = read(STAGE / 'manifest.json')
    manifest_sha = sha(STAGE / 'manifest.json')
    checks = read(STAGE / 'geometry-checks.json')
    assert checks['passed'] and checks['manifest_sha256'] == manifest_sha
    assert checks['checker_sha256'] == sha(ROOT / 'Tools/belltower_check_forest_distribution.py')
    for path, expected in manifest['source_sha256'].items():
        assert sha(ROOT / path) == expected, path
    imported = read(STAGE / 'native-import-result.json')
    assert imported['ManifestSha256'] == manifest_sha and imported['Imported'] == 48
    assert imported['GamePreserved'] and imported['SelectedDocumentPreserved'] and not imported['SceneSaved']
    shared = ('Capture', 'Projection', 'Lighting', 'NativeExposureAfterRender', 'TrialLook',
              'MainPostprocessSynced', 'SourceSceneSha256', 'CaptureHelperSha256', 'ForestCoverageParameters')
    views = []
    for view, rectangle in (('west-ridge', (900, 410, 1100, 438)), ('west-ridge-detail', (1000, 150, 1300, 260))):
        metadata, images = {}, {}
        for label, variant, models in (('baseline', 'accepted', 0), ('control', 'control', 8), ('clumped', 'clumped', 8)):
            folder = QUALITY / f'forest-distribution-v1-native-{label}'
            value = read(folder / f'{view}-camera.json')
            assert value['DistributionVariant'] == variant and value['DistributionModels'] == models
            assert value['DistributionManifestSha256'] == manifest_sha
            assert value['CaptureHelperSha256'] == sha(ROOT / 'Sources/Belltower/editor/capture-forest-distribution.cs.txt')
            assert value['SourceSceneSha256'] == sha(ROOT / 'Assets/scenes/maps/Belltower/belltower.scene')
            assert value['GamePreserved'] and value['SelectedDocumentPreserved'] and not value['SceneHasUnsavedChanges']
            assert value['TrialForestCoverageSlots'] == 88 and value['ForestCoverageParameters']['StrengthOverride'] == 0
            assert value['TrialLook'] == dict(minimum_exposure=2, maximum_exposure=2, compensation=0, mode='ACES')
            assert read(folder / f'{view}-restore.json') == dict(MaterialsRestored=True, Slots=88)
            assert read(folder / f'{view}-look-restore.json') == dict(ToneRestored=True)
            assert read(folder / f'{view}-distribution-restore.json') == dict(ModelsRestored=True, Models=models)
            metadata[label], images[label] = value, folder / f'{view}.png'
        assert all(metadata['baseline'][key] == metadata[label][key] for key in shared for label in ('control', 'clumped'))
        arrays = {key: pixels(path) for key, path in images.items()}
        x0, y0, x1, y1 = rectangle
        control = np.abs(arrays['baseline'][y0:y1, x0:x1] - arrays['control'][y0:y1, x0:x1])
        control_passed = float(control.mean()) < .1
        candidate = np.abs(arrays['baseline'][y0:y1, x0:x1] - arrays['clumped'][y0:y1, x0:x1])
        repeat_folder = QUALITY / 'forest-distribution-v1-native-repeat'
        repeated = read(repeat_folder / f'{view}-camera.json')
        assert all(metadata['baseline'][key] == repeated[key] for key in shared)
        repeat_pixels = pixels(repeat_folder / f'{view}.png')
        repeat_difference = np.abs(arrays['baseline'][y0:y1, x0:x1] - repeat_pixels[y0:y1, x0:x1])
        views.append(dict(view=view, images={key: dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path)) for key, path in images.items()},
                          control_forest_mean_abs_rgb_8bit=float(control.mean()), candidate_forest_mean_abs_rgb_8bit=float(candidate.mean()),
                          control_threshold_mean_abs_rgb_8bit=.1, control_passed=control_passed,
                          later_hidden_repeat_forest_mean_abs_rgb_8bit=float(repeat_difference.mean()),
                          later_hidden_repeat_scope='Captured after returning selection to Lowtide. The large brightness shift makes it unsuitable as a temporal noise calibration for the active-tab batch.',
                          region=list(rectangle), matched_recorded_inputs=True, original_models_and_materials_restored=True))
    report = dict(status='Density-only candidate withheld: patchy appearance and native image control above threshold.', manifest_sha256=manifest_sha,
                  native_model_compilation_verified=True, native_control_passed=all(v['control_passed'] for v in views), views=views,
                  source_original_cards=52986, source_candidate_cards=41137, source_removed_cards=11849,
                  unchanged_sectors=80, trial_sectors=8,
                  material_scope='All variants temporarily use the same private coverage material at strength zero, with unchanged distance fade.',
                  exposure_scope='Fixed ACES exposure 2 for all variants, restored after each image.',
                  accepted=False, visual_review='Provisional visual rejection: the new gaps show pale terrain between trees and read as patchy cutouts. The control exceeds the strict image gate, so these captures do not establish a fully isolated geometry comparison. Do not promote.',
                  next_visual_work='Resolve viewport exposure consistency before a new acceptance comparison. Investigate crown variation/shape and canopy-to-terrain continuity rather than adopting density-only thinning.',
                  performance_scope='Source triangle count is lower in the eight trial sectors. No gameplay timing or FPS improvement is established.',
                  selected_scene_after_review='scenes/maps/lowtide/lowtide.scene', playing_after_review=False,
                  accepted_scene_changed=False, accepted_shader_changed=False, trial_promoted=False,
                  overall_quality_goal_complete=False)
    target = STAGE / 'native-review.json'
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(native_control_views=2, native_control_passed=report['native_control_passed'], models_restored_per_trial=8, material_slots_restored=88,
                          density_candidate_accepted=False, selected_scene_restored='lowtide')))


if __name__ == '__main__':
    main()
