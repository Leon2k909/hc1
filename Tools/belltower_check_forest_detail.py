"""Check source-space canopy colour calibration and the current atlas usage."""
from collections import Counter
import json
from pathlib import Path
import re

import numpy as np

import belltower_forest_detail_trial as F


def main():
    manifest_path = F.OUT / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    data = json.loads((F.OUT / 'calibration.json').read_text(encoding='utf-8'))
    assert F.sha(F.OUT / 'calibration.json') == manifest['calibration_sha256']
    for relative, expected in manifest['source_sha256'].items():
        assert F.sha(F.ROOT / relative) == expected, relative
    for record in manifest['files']:
        assert F.sha(F.ROOT / record['source']) == record['sha256']
    assert len(manifest['files']) == 2
    old_shader = F.ACCEPTED_SHADER.read_text(encoding='utf-8')
    new_shader = (F.OUT / 'Assets' / F.TRIAL_SHADER).read_text(encoding='utf-8')
    tail = '        m.Roughness = .9;'
    assert old_shader[old_shader.index(tail):] == new_shader[new_shader.index(tail):], 'Lighting/normal/fog tail changed'
    alpha = lambda text: text[text.index('        m.Opacity ='):text.index('        float2 plan =')]
    assert alpha(old_shader) == alpha(new_shader), 'Opacity behaviour changed'
    assert old_shader.count('.Sample(') == new_shader.count('.Sample(')
    assert old_shader.count('.SampleLevel(') == new_shader.count('.SampleLevel(')
    properties = lambda text: dict(re.findall(r'^\s*(\w+)\s+"([^"\n]+)"', text, re.MULTILINE))
    old_material = properties(F.ACCEPTED_MATERIAL.read_text(encoding='utf-8'))
    new_material = properties((F.OUT / 'Assets' / F.TRIAL_MATERIAL).read_text(encoding='utf-8'))
    assert all(new_material[key] == value for key, value in old_material.items() if key != 'shader')
    assert new_material['shader'] == F.TRIAL_SHADER

    # Inspect actual current mesh UV indices, rather than assuming the source
    # generator's unused fourth atlas variant is also absent from installed OBJ.
    group = json.loads((F.ROOT / 'Sources/Belltower/landscape/forest.json').read_text(encoding='utf-8'))
    variants = Counter()
    meshes = []
    for child in group['Children']:
        model = child['Components'][0]['Model']
        relative = model['Path'] if isinstance(model, dict) else model
        obj = (F.ROOT / 'Assets' / relative).with_suffix('.obj')
        with obj.open(encoding='utf-8') as stream:
            uv_count = 0
            for line in stream:
                if line.startswith('vt '):
                    uv_count += 1
                elif line.startswith('f '):
                    indices = [(int(token.split('/')[1]) - 1) // 8 for token in line.split()[1:]]
                    assert len(indices) == 3 and len(set(indices)) == 1 and indices[0] in range(4)
                    variants[indices[0]] += 1
        assert uv_count == 32
        meshes.append(obj.relative_to(F.ROOT).as_posix())
    assert len(meshes) == 88 and sum(variants.values()) == 640000
    assert set(variants) == {0, 1, 3}
    for cell in data['cells']:
        assert abs(cell['candidate_mean'] / cell['current_mean'] - 1) < 1e-6
        assert max(abs(value / cell['current_mean'] - 1) for value in cell['candidate_rgb_mean']) < 1e-6
        assert cell['highlight_std_before'] < 1e-12 and cell['highlight_std_after'] > .01
        assert cell['shadow_std_before'] < 1e-12 and cell['shadow_std_after'] > .001
        assert np.all(np.diff(F.response(np.linspace(0, 1, 65536), cell['knee'])) > 0)
    rgb_drift = max(abs(value) for mip in data['mip_proxy'][:6] for cell in mip['variants']
                    if cell['variant'] in variants for value in cell['relative_rgb_mean_drift'])
    assert rgb_drift < .02, 'Mip proxy changes the used trees by over 2 percent in a colour channel'

    # Regression for the rejected blue fringe: unreliable-alpha colour must
    # become neutral AFTER normalization, for every channel and atlas variant.
    rgb = np.array([[1., 0., 1.], [0., 1., 0.], [.2, .2, .2]])
    luma = rgb @ np.array([.2126, .7152, .0722])
    raw, confidence = F.source_chroma(rgb, luma, np.array([.35, .5, .65]))
    for mean in data['chroma_means']:
        corrected = 1 + data['chroma_strength'] * confidence[:, None] * (raw / mean - 1)
        assert np.array_equal(corrected, np.ones_like(corrected))
        rejected = (1 + confidence[:, None] * (raw - 1)) / mean
        assert np.max(np.abs(rejected - 1)) > .1, 'Regression fixture no longer exercises the old error'
    report = dict(passed=True, scope='Source shader/calibration checks, not native compilation, lighting, BC7 or performance.',
                  manifest_sha256=F.sha(manifest_path), checker_sha256=F.sha(Path(__file__)),
                  installed_forest_meshes_inspected=len(meshes), triangles_by_atlas_variant=dict(variants),
                  base_colour_mean_relative_error_max=max(abs(v / cell['current_mean'] - 1) for cell in data['cells'] for v in cell['candidate_rgb_mean']),
                  used_mip_0_to_5_rgb_drift_max=rgb_drift, mip_proxy_limit=.02,
                  alpha_normals_lighting_and_fog_preserved=True, texture_sample_calls_unchanged=True,
                  rejected_fringe_fixture_detected=True, unreliable_colour_falls_back_to_neutral=True,
                  texture_inputs_changed=False, geometry_changed=False, native_verified=False)
    (F.OUT / 'checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
