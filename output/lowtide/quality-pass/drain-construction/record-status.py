"""Record the reviewed offline drainage candidate without touching live assets."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
base = Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((base/'manifest.json').read_text())
checked = json.loads((base/'verification.json').read_text())
preview = json.loads((base/'preview/provenance.json').read_text())
assert checked['manifest_sha256'] == preview['manifest_sha256'] == sha(base/'manifest.json')
assert checked['verifier_sha256'] == preview['reviewer_sha256'] == sha(root/'Tools/lowtide_drain_review.py')
assert preview['geometry_generator_sha256'] == sha(root/'Tools/lowtide_drain_construction.py')
assert all(sha(root/p) == h for p, h in manifest['protected'].items())
assert all(sha(base/'preview'/p) == h for p, h in preview['previews'].items())
assert not (root/'Assets/shaders/hc1_lowtide_finish_metal.shader').exists()
status = dict(
    date='2026-10-15', revision=manifest['revision'], status='offline_candidate_awaiting_native_review',
    native_accepted=False, production_changed=False, canonical_generator_changed=False,
    geometry=dict(pipes=len(manifest['layout']), removed_triangles=manifest['removed_triangles'],
                  candidate_triangles=manifest['candidate_triangles'], delta_triangles=manifest['delta_triangles'],
                  unchanged_triangles=manifest['unchanged_triangles'],
                  description='Continuous curved hollow shoes, tapered open hoppers, cast socket profiles and fixed wall plates.',
                  collision_changed=False, new_material_slots=0),
    material_mapping=dict(source_size=manifest['staged_material_changes']['source_size'],
                          atlas_size=manifest['staged_material_changes']['atlas_size'],
                          source_pixels_preserved=True, shader_compiled=False,
                          physical_tile_inches=manifest['staged_material_changes']['physical_tile_inches'],
                          description='Original scan repeats inside its valid atlas rectangle; eliminates sampling of the edge padding.',
                          affected_materials=list(manifest['staged_material_changes']['changes']),
                          scope=manifest['staged_material_changes']['scope'],
                          independent_of_geometry=True),
    evidence=dict(manifest=(base/'manifest.json').relative_to(root).as_posix(),
                  manifest_sha256=sha(base/'manifest.json'), verification=checked,
                  preview=(base/'preview/provenance.json').relative_to(root).as_posix(),
                  reviewed_comparisons=[f'output/lowtide/quality-pass/drain-construction/preview/{name}-{variant}.png'
                                        for name in ('shoe', 'hopper', 'fixing')
                                        for variant in ('comparison', 'geometry-comparison')],
                  initial_preview='output/lowtide/quality-pass/drain-construction/first-review/review-status.json'),
    integration=dict(
        stage='output/lowtide/quality-pass/drain-construction/stage',
        new_shader='shaders/hc1_lowtide_finish_metal.shader (expected absent in live Assets; recheck before promotion)',
        material_only='The two material changes and their new shader can be evaluated with the existing geometry.',
        geometry='Only lowtide_finish.obj is replaced after fresh before-hash checks; retain its unchanged material library and model definition.',
        other_candidates='Does not overlap window/door OBJ or warehouse-floor VMDL stages, or dressing/fleet sack models.',
        remaining=[
            'Keep the user-requested offline mode until the human changes it.',
            'Compile and inspect the shader/material correction in the normal native viewport, including gutters, grates and anchors.',
            'Inspect hopper/gutter/roof connections in the map; isolated drain previews do not establish complete rainwater connections.',
            'Profile the additional geometry, shadow cost and distant aliasing before deciding on promotion or lower detail.',
            'If accepted, integrate scoped drainage/material hooks into the canonical finish generator and verify saving and persistence.',
            'The overall AAA visual goal remains open.'
        ]))
path = root/'Sources/Lowtide/drainage/construction-status.json'
composed_status = root/'Sources/Lowtide/drainage/junction-status.json'
if composed_status.exists():
    composed = json.loads(composed_status.read_text())
    composed_manifest = json.loads((root/composed['evidence']['manifest']).read_text())
    if composed_manifest['baseline_manifest_sha256'] == sha(base/'manifest.json'):
        status['geometry']['direct_promotion_superseded'] = True
        status['integration']['current_composed_junction_candidate'] = composed_status.relative_to(root).as_posix()
        status['integration']['geometry'] = 'The isolated geometry intersects saved cornices/gutters; use the composed junction candidate for native review. Its material correction remains valid independently.'
path.write_text(json.dumps(status, indent=2)+'\n')
handoff = root/'Sources/Lowtide/construction/offline-status.json'
before = handoff.read_bytes()
data = json.loads(before)
data['separate_pending_work']['drainage_construction_and_atlas_mapping'] = path.relative_to(root).as_posix()
temporary = handoff.with_suffix('.drainage.tmp')
assert not temporary.exists()
temporary.write_text(json.dumps(data, indent=2)+'\n')
assert handoff.read_bytes() == before
temporary.replace(handoff)

notes = root/'CLAUDE.md'
before = notes.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
marker = b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)' + newline
note = '''- Offline drainage construction and material mapping (2026-10-15): read
  `Sources/Lowtide/drainage/construction-status.json`. The candidate replaces 36 capped/blocky
  drains with curved hollow outlets, tapered open hoppers, socket profiles and wall fixings.
  It adds 95,504 triangles to `lowtide_finish`; the other 71,642 triangles remain unchanged.
  Close CPU previews exposed a separate material defect: the two drain materials sampled the
  padded borders of the 2048-square steel atlas. The staged shader limits repeats to the original
  1254-square source at its authored 24-inch scale, preserving all colour/normal pixels. It also
  corrects those shared slots on gutters, grates and anchors, independently of the geometry.
  Six comparison sheets separate the mapping fix from the shape change. Manifold, aperture,
  source-pixel, reconstruction and reproduction checks pass; 556 protected live files are unchanged.
  Native shader compilation, map roof/gutter connections, distance appearance and geometry/shadow
  cost remain unverified. No canonical hook, live promotion or overall quality acceptance is applied.
  Keep the user's offline restriction; use `Tools/lowtide_drain_construction.py` and
  `Tools/lowtide_drain_review.py` for this separate candidate.
'''.encode().replace(b'\n', newline)
assert before.count(marker) == 1
if b'- Offline drainage construction and material mapping (2026-10-15)' not in before:
    temporary = notes.with_name('.CLAUDE.lowtide-drainage-note.tmp')
    assert not temporary.exists()
    temporary.write_bytes(before.replace(marker, marker+note, 1))
    assert notes.read_bytes() == before, 'Documentation changed concurrently'
    temporary.replace(notes)
print('Recorded offline drainage candidate; native acceptance remains pending.')
