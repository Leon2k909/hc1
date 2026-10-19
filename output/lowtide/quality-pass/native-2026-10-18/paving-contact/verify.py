import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_paving_use as U
import lowtide_grates as G
import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent
manifest = json.loads((BASE / 'manifest.json').read_text())
for name, expected in manifest['sources'].items():
    assert U.sha(ROOT / name) == expected, name
for name, expected in manifest['staged_files'].items():
    assert U.sha(BASE / 'stage' / name) == expected, name
assert U.contact_material((U.ASSETS / U.MATERIAL).read_text()) == (BASE / 'stage' / U.MATERIAL).read_text()
assert U.shader() == (BASE / 'stage' / U.SHADER).read_text()
outlets = U.current_drain_outlets()
assert len(outlets) == len(manifest['outlets']) == 36
for a, b in zip(outlets, manifest['outlets']):
    assert a['kind'] == b['kind'] and np.allclose(a['position'], b['position'], atol=1e-10)
ground, segments, _ = U.saved_surfaces()
pixels, _ = U.fields(ground, segments, outlets, manifest['settings'])
with Image.open(BASE / 'stage' / U.MASK) as im:
    assert np.array_equal(pixels, np.asarray(im))
hole_checks = 0
for e, n, width, length in G.layout():
    for dx in (-width/2+5, 0, width/2-5):
        for dy in (-length/2+5, 0, length/2-5):
            x, y = np.rint(U.pixel([[e+dx, n+dy]], manifest['settings'])[0]).astype(int)
            assert not pixels[y, x].any(), (e, n, x, y, pixels[y, x].tolist())
            hole_checks += 1
assert len(ground) == manifest['ground_triangles'] == 186
report = dict(material_and_shader_reproduce=True, mask_reproduces=True,
              canonical_outlets_match=36, grate_interior_samples_clear=hole_checks,
              production_sources_unchanged=True, generator_sha256=U.sha(ROOT / 'Tools/lowtide_paving_use.py'),
              native_review_complete=False)
U.write(BASE / 'verification.json', json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
