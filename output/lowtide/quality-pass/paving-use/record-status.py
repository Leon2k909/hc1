"""Record the reviewed offline paving candidate; do not install any asset."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


manifest = read(BASE/'manifest.json')
checked = read(BASE/'verification.json')
preview = read(BASE/'preview/provenance.json')
assert checked['manifest_sha256'] == preview['manifest_sha256'] == sha(BASE/'manifest.json')
assert checked['reviewer_sha256'] == preview['renderer_sha256'] == sha(ROOT/'Tools/lowtide_paving_use_review.py')
assert all(sha(ROOT/p) == digest for p, digest in manifest['sources'].items())
assert all(sha(ROOT/p) == digest for p, digest in manifest['protected'].items())
assert all(sha(BASE/'stage'/p) == sha(BASE/'reproduction/stage'/p) == digest for p, digest in manifest['staged_files'].items())
assert (BASE/'manifest.json').read_bytes() == (BASE/'reproduction/manifest.json').read_bytes()
assert len(preview['files']) == 6
assert all(sha(BASE/'preview'/p) == digest for p, digest in preview['files'].items())
assert all(sha(ROOT/p) == digest for p, digest in preview['renderer_dependencies'].items())
assert all(sha(ROOT/p) == digest for p, digest in preview['source_geometry'].items())
assert all(sha(ROOT/'Assets'/p) == digest for p, digest in preview['original_texture_inputs'].items())
reproduction = dict(status='byte_identical_reproduction_passed', manifest_sha256=sha(BASE/'manifest.json'),
                    byte_identical_staged_files=len(manifest['staged_files']), identical_manifest=True,
                    files=manifest['staged_files'])
write(BASE/'reproduction-verification.json', reproduction)

atlas = read(BASE.parent/'atlas-audit/inventory.json')
status = dict(date='2026-10-15', status='offline_candidate_ready_for_native_review',
              revision=manifest['revision'], user_work_mode='Continue offline for now',
              production_changed=False, native_accepted=False, canonical_generator_changed=False,
              generator='Tools/lowtide_paving_use.py', reviewer='Tools/lowtide_paving_use_review.py',
              settings='Sources/Lowtide/paving/edge-use.json', shader_extension='Sources/Lowtide/paving/edge-use.hlsl',
              changes=[
                  'Narrow settled grit follows 1,408 deduplicated wall-foot segments extracted from saved geometry.',
                  'Local moisture fields sit near 16 staged drain outlets over the existing granite paving.',
                  'Original generated stone colour, normal, roughness, AO and nine-millimetre relief are preserved.',
                  'The existing broad paving variation remains; local moisture only increases its wet response.',
                  'Only the existing Lowtide setts material is staged: no model remaps, material slots, geometry or collision changes.'],
              scope=dict(ground_triangles=len(manifest['ground']), wall_segments=len(manifest['wall_segments']),
                         drain_outlets_over_setts=checked['drain_outlets_over_setts'],
                         atlas_pixels=manifest['settings']['atlas_pixels'], channels=manifest['channels'],
                         coverage_above_point1=manifest['coverage_over_existing_setts'],
                         delta_triangles=0, new_material_slots=0, model_remaps=0, extra_texture_lookups=1),
              evidence=dict(manifest='output/lowtide/quality-pass/paving-use/manifest.json',
                            manifest_sha256=sha(BASE/'manifest.json'),
                            verification='output/lowtide/quality-pass/paving-use/verification.json',
                            reproduction='output/lowtide/quality-pass/paving-use/reproduction-verification.json',
                            views='output/lowtide/quality-pass/paving-use/preview/provenance.json',
                            atlas_samples=checked['atlas_samples'], excluded_surface_samples=checked['excluded_surface_samples'],
                            moisture_texels_checked=checked['moisture_texels_checked'],
                            byte_identical_staged_files=len(manifest['staged_files']),
                            protected_live_files_unchanged=len(manifest['protected'])),
              preview=dict(kind='Six matched CPU material/context views', native_engine_capture=False,
                           visual_review='Reviewed both versions at the quay shed, warehouse street and shed wall base. The local changes are restrained; native response remains unproven.',
                           limitations=['Neutral clipped architecture, same staged drains in both versions',
                                        'Approximate CPU light, normal maps, relief and mip filtering',
                                        'Native lighting, shader compilation, compression, temporal filtering and performance are untested']),
              first_review=dict(directory='output/lowtide/quality-pass/paving-use/first-review',
                                reason='Wider brighter framing made the narrow contact fields difficult to assess; final views are closer with matched lower CPU exposure. Candidate assets are unchanged.'),
              atlas_audit=dict(report='output/lowtide/quality-pass/atlas-audit/inventory.json',
                               report_sha256=sha(BASE.parent/'atlas-audit/inventory.json'),
                               materials=len(atlas['materials']), unique_png_inputs=len(atlas['textures']),
                               finding='Only the already staged drain mapping defect was confirmed among the repeated-border candidates. Existing bridge deck and distant shipyard meshes use bounded atlas UVs.',
                               limitation='Exact repeated-border detection and targeted UV checks, not a proof of every possible texture or filtering defect.'),
              integration=dict(stage='output/lowtide/quality-pass/paving-use/stage',
                               material='materials/lowtide/lt_setts.vmat',
                               live_target_states={p:(sha(ROOT/'Assets'/p) if (ROOT/'Assets'/p).is_file() else None)
                                                   for p in manifest['staged_files']},
                               drainage_dependency='Sources/Lowtide/drainage/junction-status.json',
                               native_followup=[
                                   'Keep offline mode until the user resumes native work; start with fresh editor/project/compile/scene/play/unsaved state.',
                                   'Revalidate the manifest, all before hashes and recorded absent target paths. Compile the new shader and an unused review material through the editor.',
                                   'Use the normal existing viewport and scoped temporary material overrides for comparison; preserve camera, tab, scene and play state.',
                                   'Inspect wall contact, outlet alignment, roughness, atlas boundaries, distance filtering and cost under actual map lighting. This is a static art layout, not a fluid simulation.',
                                   'After acceptance, promote only the five listed files and integrate this material extension with the canonical paving generator. No whole model snapshot or scene replacement is needed.',
                                   'Save and verify persistence; do not claim overall AAA quality from these offline views.']),
              overall_goal='Open: map-wide native appearance and gameplay performance are not established')
write(ROOT/'Sources/Lowtide/paving/use-status.json', status)
master_path = ROOT/'Sources/Lowtide/construction/offline-status.json'
master_bytes = master_path.read_bytes()
master = json.loads(master_bytes)
master['separate_pending_work']['exterior_paving_contact'] = 'Sources/Lowtide/paving/use-status.json'
assert master_path.read_bytes() == master_bytes
write(master_path, master)

# CLAUDE.md is shared with other chats. Preserve every unrelated byte and abort
# if it changes between reading and the atomic replacement.
path = ROOT/'CLAUDE.md'
before = path.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
marker = b'## Lowtide (multiplayer map, `Tools/lowtide_map.py`)'+newline
note = '''- Offline paving contact (2026-10-15): `Sources/Lowtide/paving/use-status.json` records
  a separate material candidate with narrow settled grit at saved wall feet and local moisture
  near 16 drain outlets. Original stone colour/PBR pixels and nine-millimetre relief are unchanged.
  One numerical 2048-square RGB mask adds one texture lookup; no geometry, collision, model remaps
  or material slots change. All five staged files reproduce byte for byte, 557 protected live files
  are unchanged, and 12,000 atlas samples, 228 excluded-surface cases and 4,692 moisture texels pass.
  Six matched CPU context views have been inspected. Native shader compilation, appearance,
  filtering, cost, canonical integration and persistence remain pending. Keep offline mode.
  Use `output/lowtide/quality-pass/paving-use/stage` for later scoped review; its moisture positions
  reference the composed drainage junction candidate. This does not establish overall AAA quality.
  A separate 98-material / 41-PNG repeated-border audit found no further confirmed padding defect:
  the bridge decking and distant shipyard have bounded UVs; the known drain fix remains staged.
'''.encode().replace(b'\n', newline)
assert before.count(marker) == 1
if b'- Offline paving contact (2026-10-15):' not in before:
    after = before.replace(marker, marker+note, 1)
    temporary = ROOT/'CLAUDE.lowtide-paving.tmp'
    assert not temporary.exists()
    temporary.write_bytes(after)
    assert path.read_bytes() == before
    os.replace(temporary, path)
print(json.dumps(dict(status=status['status'], staged_files=5, protected_live_files=557,
                      preview_files=6, source_status='Sources/Lowtide/paving/use-status.json'), indent=2))
