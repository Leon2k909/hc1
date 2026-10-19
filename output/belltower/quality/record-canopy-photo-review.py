"""Record the offline review; never publish or accept an engine asset."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUALITY = ROOT/'output/belltower/quality'
hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
checks = json.loads((QUALITY/'canopy-photo-v2-checks.json').read_text())
for path, digest in checks['sources'].items():
    assert hash_file(ROOT/path) == digest
assert hash_file(ROOT/'Sources/Belltower/generated/canopy-crowns-v2.png') == checks['original_atlas_sha256']
scene_digest = hash_file(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
assert scene_digest == 'aef98ef9fc0c4e484f6456f31dccc58f27163eb339e4844ebfa251de0333154a'
views = [
    ('overlap-before', 'canopy-photo-v1-swatch/photographic.png'),
    ('overlap-after', 'canopy-photo-v2-zone-b/photographic.png'),
    ('near-town-before', 'canopy-v1-zone-b/accepted/vista_b_color.jpg'),
    ('near-town-after', 'canopy-photo-v2-zone-b/vista_b_color.jpg'),
    ('distant-before', 'canopy-photo-v2-zone-c/accepted/vista_c_color.jpg'),
    ('distant-after', 'canopy-photo-v2-zone-c/photographic/vista_c_color.jpg'),
]
trials = ['canopy-photo-v2-zone-b/trial.json',
          'canopy-photo-v2-zone-c/accepted/trial.json',
          'canopy-photo-v2-zone-c/photographic/trial.json']
for path in trials:
    for source, digest in json.loads((QUALITY/path).read_text())['sources'].items():
        assert hash_file(ROOT/source) == digest
report = {
    'reviewed_utc': datetime.now(timezone.utc).isoformat(),
    'state': 'offline candidate retained for native comparison; no landscape assets published',
    'images': [{'name': name, 'path': 'output/belltower/quality/'+path, 'sha256': hash_file(QUALITY/path)} for name, path in views],
    'findings': [
        'The original trial cut whole photographic crowns along analytic dome intersections, making straight overlap edges. The unshadowed diagnostic reproduces those edges.',
        'Layering natural broadleaf crowns by summit height removes those straight cuts in the matching construction view and retains the original alpha silhouettes.',
        'The 2048px zone B comparison improves natural crown detail. The orchard trees and field layout are retained.',
        'The 1024px zone C comparison retains the large woodland and field pattern. Detail at this reduced resolution is subtle and does not establish a native visual improvement.',
    ],
    'checks': checks,
    'swatch': json.loads((QUALITY/'canopy-photo-v2-zone-b/swatch.json').read_text()),
    'trials': trials,
    'scene_sha256': scene_digest,
    'limitations': [
        'These are texture construction views, not engine screenshots.',
        'The summit ordering is a 2.5D approximation, and analytic ellipsoid shadows do not follow every leaf silhouette.',
        'Only four generated natural crown variants are available; repetition still needs review at native scale.',
        'Zone B uses 2048px and zone C uses 1024px here; the accepted landscape uses 4096px colour textures.',
        'Full-resolution zone boundaries, native foliage colour matching, lighting and gameplay performance remain to be checked.',
    ],
    'next_step': 'Prepare full-resolution matching texture trials and review valley/ridge views in a later coordinated editor window. Do not overwrite the accepted landscape manifest from this offline review.',
}
(QUALITY/'canopy-photo-v2-review.json').write_text(json.dumps(report, indent=2)+'\n')

path = ROOT/'CLAUDE.md'
before = path.read_bytes()
text = before.decode('utf-8')
anchor = '  - Stage landscape textures with `belltower_vista_paint.py --out <output directory>` (four CPU threads), then'
assert text.count(anchor) == 1
addition = '''  - Offline canopy candidates (2026-10-15) have not changed the accepted landscape. `belltower_canopy_trial.py`
    stages procedural variants; `belltower_photographic_canopy.py` uses the original built-in ImageGen RGBA atlas
    `Sources/Belltower/generated/canopy-crowns-v2.png`. Its JSON preserves the edit prompt and provenance; the v1
    original is also retained. The atlas alpha is unchanged, including occasional alpha=1 pixels in the gaps.
    Natural oak/holm/beech/willow crowns use premultiplied linear filtering; planted trees keep the accepted painter.
    The first photo trial had straight overlap cuts from intersecting analytic domes. V2 layers whole crowns by
    summit height with world-coordinate tie breakers. `canopy-photo-v2-checks.json` verifies input-order invariance,
    matching tile edges, unchanged planted trees and all four species; the check rejects the original painter.
    `canopy-photo-v2-review.json` records the reviewed swatch, 2048px zone B and 1024px zone C comparisons. Coverage
    in the matching grove is 79.87% versus the accepted 80.87%. Ellipsoid shadows remain approximate, and distant
    texture detail/repetition still need full-resolution and native review. All candidates stay under quality output;
    the accepted landscape generator, live textures, tree placement and scene are unchanged.
'''
text = text.replace(anchor, addition+anchor)
anchor = '    natively yet. `aces-fixed-low` and `aces-fixed-high` use 0.35 and 2.0 bounds to make the next comparison decisive.'
assert text.count(anchor) == 1
text = text.replace(anchor, anchor+'''
    The latest helper also sets horizontal FOV and bitmap dimensions after its streaming wait and restores those
    projection values afterward. The installed SceneViewportWidget resets projection each editor frame, as confirmed
    independently by Cerro Blanco's capture work and the local source. This helper renders synchronously after setup;
    its new `Projection` metadata and main-camera diagnostic still await native validation. The read-only camera
    probe reads `IsSceneEditorCamera` as a field, matching the installed engine IL. Copy fresh helpers from source
    for the next window; the earlier exchange copies predate these offline changes.''')
incoming = path.with_name('CLAUDE.belltower-canopy.tmp')
assert not incoming.exists()
incoming.write_text(text, encoding='utf-8', newline='')
assert path.read_bytes() == before, 'Concurrent CLAUDE edit; inspect before replacing.'
incoming.replace(path)
print(json.dumps({'review':'output/belltower/quality/canopy-photo-v2-review.json',
                  'images_reviewed':len(views), 'landscape_published':False}))
