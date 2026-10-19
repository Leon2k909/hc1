"""Record junction context review and the current composed offline finish mesh."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[4]
base = Path(__file__).resolve().parent
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest = json.loads((base/'manifest.json').read_text())
checked = json.loads((base/'verification.json').read_text())
preview = json.loads((base/'preview/provenance.json').read_text())
assert checked['manifest_sha256'] == sha(base/'manifest.json')
assert checked['verifier_sha256'] == sha(root/'Tools/lowtide_drain_junction_verify.py')
assert preview['reviewer_sha256'] == sha(root/'Tools/lowtide_drain_context.py')
assert all(sha(root/p) == h for p, h in manifest['sources'].items())
assert all(sha(root/p) == h for p, h in manifest['protected'].items())
assert all(sha(root/p) == h for p, h in preview['source_files'].items())
assert all(sha(base/'preview'/p) == h for p, h in preview['previews'].items())
status = dict(
    date='2026-10-15', revision=manifest['revision'], status='offline_candidate_awaiting_native_review',
    native_accepted=False, production_changed=False, canonical_generator_changed=False,
    scope=dict(warehouse_heads=20, shed_receivers=16, gutters=8, roof_aprons=8,
               description='Warehouse offsets and external scupper channels clear the cornice; shed receivers sit below pierced gutters moved beyond the coping, with folded roof aprons and wall-mounted brackets.',
               collision_changed=False, new_material_slots=0,
               delta_from_live=manifest['delta_from_live'], delta_from_prior_candidate=manifest['delta_from_drain_candidate'],
               unchanged_triangles=manifest['unchanged_triangles']),
    evidence=dict(manifest=(base/'manifest.json').relative_to(root).as_posix(), manifest_sha256=sha(base/'manifest.json'),
                  verification=(base/'verification.json').relative_to(root).as_posix(), checks=checked,
                  preview=(base/'preview/provenance.json').relative_to(root).as_posix(),
                  reviewed_views=sorted(preview['previews']),
                  initial_diagnostic='output/lowtide/quality-pass/drain-junctions/initial-review/provenance.json'),
    integration=dict(
        current_geometry_stage='output/lowtide/quality-pass/drain-junctions/stage',
        supersedes_geometry_stage='output/lowtide/quality-pass/drain-construction/stage',
        warning='Use this composed finish OBJ for junction review. Copying the earlier isolated-pipe stage afterward restores the cornice/gutter intersections.',
        inherited_materials='The original scan-region shader/material correction is unchanged and remains independently reviewable.',
        protected_state='All scene/model definitions, architecture OBJ files, collision and gameplay layout remain unchanged.',
        remaining=[
            'Preserve the human-requested offline mode; this stage has not been imported.',
            'Native shader compilation and normal-viewport visual checks, including wide shots and distant appearance.',
            'Controlled gameplay and shadow-cost profiling before deciding on detailed geometry promotion.',
            'Canonical generator integration, native saving and persistence after acceptance.',
            'The overall AAA quality goal remains open.'
        ]))
destination = root/'Sources/Lowtide/drainage/junction-status.json'
destination.write_text(json.dumps(status, indent=2)+'\n')

def update(path, transform):
    before = path.read_bytes()
    data = json.loads(before)
    transform(data)
    temporary = path.with_suffix('.junction-note.tmp')
    assert not temporary.exists()
    temporary.write_text(json.dumps(data, indent=2)+'\n')
    assert path.read_bytes() == before
    temporary.replace(path)

def previous(data):
    data['geometry']['direct_promotion_superseded'] = True
    data['integration']['current_composed_junction_candidate'] = destination.relative_to(root).as_posix()
    data['integration']['geometry'] = 'The isolated geometry intersects saved cornices/gutters; use the composed junction candidate for native review. Its material correction remains valid independently.'
update(root/'Sources/Lowtide/drainage/construction-status.json', previous)
update(root/'Sources/Lowtide/construction/offline-status.json',
       lambda data: data['separate_pending_work'].update(drainage_junctions=destination.relative_to(root).as_posix()))

notes = root/'CLAUDE.md'
before = notes.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
marker = b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)' + newline
note = '''- Offline drainage junction repair (2026-10-15): `Sources/Lowtide/drainage/junction-status.json`
  supersedes the isolated drain geometry stage below. Context views exposed warehouse hoppers
  embedded in the cornice and shed gutters crossing hopper mouths. The composed candidate has
  20 warehouse pipe offsets/scuppers, 16 lowered shed receivers, eight pierced gutters moved
  beyond the coping, and folded roof aprons with supporting wall brackets. The shared material
  mapping correction is unchanged. Only `lowtide_finish.obj` changes: +111,936 triangles against
  live production, including +16,432 beyond the earlier drain candidate; no new material slots.
  Geometry reconstruction/reproduction, checked closed shells, 488 exterior rain-path rays and
  20,272 clearance samples against the saved east/west architecture pass. The sampled minimum
  upper pipe/hopper clearance is 0.671 inches; the grid is not an exhaustive intersection proof.
  Eight clipped CPU context views use neutral architecture and matching corrected metal on both
  versions. All 556 protected live files remain unchanged. Native appearance, shader compilation,
  geometry/shadow cost, canonical integration and persistence remain unverified. Keep offline mode.
  Use `output/lowtide/quality-pass/drain-junctions/stage` for later native review; copying the older
  drain-only OBJ over it restores the junction defects. No overall AAA acceptance is claimed.
'''.encode().replace(b'\n', newline)
assert before.count(marker) == 1
if b'- Offline drainage junction repair (2026-10-15)' not in before:
    temporary = notes.with_name('.CLAUDE.lowtide-drain-junctions.tmp')
    assert not temporary.exists()
    temporary.write_bytes(before.replace(marker, marker+note, 1))
    assert notes.read_bytes() == before
    temporary.replace(notes)
print('Recorded composed drainage junction candidate; no live promotion.')
