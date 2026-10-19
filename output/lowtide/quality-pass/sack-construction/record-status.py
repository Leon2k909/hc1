"""Save this offline candidate only when current meshes, previews and checks agree."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n')


manifest = json.loads((OUT/'manifest.json').read_text())
checked = json.loads((OUT/'verification.json').read_text())
preview = json.loads((OUT/'final-preview/provenance.json').read_text())
assert checked['manifest_sha256'] == sha(OUT/'manifest.json')
assert checked['verifier_sha256'] == sha(ROOT/'Tools/lowtide_sack_verify.py')
assert checked['preview_renderer_sha256'] == preview['reviewer_sha256'] == sha(ROOT/'Tools/lowtide_sack_preview.py')
assert preview['generator_sha256'] == sha(ROOT/'Tools/lowtide_sack_construction.py')
assert checked['shared_renderer_sha256'] == preview['renderer_sha256'] == sha(ROOT/'Tools/lowtide_window_software.py')
assert all(sha(ROOT/p) == h for p, h in manifest['sources'].items())
assert all(sha(ROOT/p) == h for p, h in manifest['protected'].items())
assert all(sha(OUT/'stage'/p) == h['after'] for p, h in manifest['changes'].items())
assert all(sha(OUT/'final-preview'/p) == h for p, h in preview['previews'].items())
assert all(sha(OUT/'reproduction'/f'{name}-sacks.obj') == record['component_sha256'] for name, record in manifest['models'].items())
assert checked['byte_identical_reproduced_components'] == 3
status = dict(date='2026-10-15', revision=manifest['revision'],
    status='offline_geometry_candidate_native_review_pending', production_changed=False,
    generator='Tools/lowtide_sack_construction.py', verifier='Tools/lowtide_sack_verify.py',
    changes=['Pinched sewn ends and an embedded longitudinal hem replace the rounded box shape.',
             'Local gathers and small asymmetry vary each filled sack within its saved cover bounds.',
             'The same generated jute pixels wrap continuously around the body at a finer 13.3 cm tile scale.',
             'No live material, collision, scene, placement or other prop faces change.'],
    scope=dict(sacks=checked['sacks'], models=3, triangles_per_sack=1570,
               delta_triangles=manifest['delta_triangles'], new_material_slots=0),
    evidence=dict(manifest='output/lowtide/quality-pass/sack-construction/manifest.json',
                  manifest_sha256=sha(OUT/'manifest.json'),
                  verification='output/lowtide/quality-pass/sack-construction/verification.json',
                  preview='output/lowtide/quality-pass/sack-construction/final-preview/provenance.json',
                  exported_closed_meshes=checked['sacks'], protected_files_unchanged=len(manifest['protected']),
                  byte_identical_reproduced_components=3),
    preview=dict(native_engine_capture=False,
                 review='The six final matched single-sack, sewn-mouth and stack views were reviewed. The complete stack is framed and the false triangular self-shadows are removed.',
                 renderer_fix='A local half-pixel shadow adapter matches rasterized and receiver depth coordinates; analytic sloped-plane checks cover it. Existing shared renderer and prior candidate evidence are unchanged.',
                 limitations=preview['limitations']),
    integration=dict(canonical_writer_integrated=False, native_accepted=False,
        independent_from='The window/door OBJ and timber/concrete VMDL stages use different model paths.',
        next=['Keep the user-requested offline mode until native work is resumed.',
              'Recheck live source hashes before any import; preserve later dressing/fleet edits.',
              'Use the existing normal viewport to inspect end closures, contact, textile filtering and actual warehouse lighting; preserve camera/tab/play state.',
              'Measure the added geometry cost in a match and choose distance reduction or instancing if needed. Offline renders do not prove a performance budget.',
              'Only after acceptance integrate the sack builder into canonical generation, compile, refresh affected lighting and verify saved persistence.']),
    overall_goal='Open: neither native acceptance nor AAA quality is established by this candidate')
lod_manifest = ROOT/'output/lowtide/quality-pass/sack-lods/manifest.json'
if lod_manifest.exists():
    lod = json.loads(lod_manifest.read_text())
    if lod.get('baseline_manifest_sha256') == sha(OUT/'manifest.json'):
        status['integration']['distance_detail_candidates'] = 'Sources/Lowtide/sacks/lod-status.json'
write(ROOT/'Sources/Lowtide/sacks/construction-status.json', status)
path = ROOT/'Sources/Lowtide/construction/offline-status.json'
before = path.read_bytes()
main = json.loads(before)
main['separate_pending_work']['sewn_cargo_sacks'] = 'Sources/Lowtide/sacks/construction-status.json'
main['separate_pending_work']['sack_integration'] = 'Three dressing/fleet OBJ copies form a separate set; they do not overlap the window/door geometry or timber/concrete material stages. Revalidate before hashes before using any snapshot.'
assert path.read_bytes() == before
write(path, main)
print(json.dumps(dict(status=status['status'], sacks=checked['sacks'],
                      protected_live_files=len(manifest['protected']), delta_triangles=manifest['delta_triangles']), indent=2))
