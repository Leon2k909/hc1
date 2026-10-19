"""Record scoped offline validation in the canonical checkout; never promote assets."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
assert ROOT == Path('C:/sbox-projects/hc1/forked-shooter-main')
cache = {}


def sha(path):
    path = Path(path)
    if path not in cache:
        with path.open('rb') as stream:
            cache[path] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return cache[path]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    assert path.resolve().is_relative_to(ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')


records, protected = {}, {}
for name in ('sacks', 'water-filter-gentle', 'paving-use'):
    directory = OUT/name
    manifest_path = directory/'manifest.json'
    manifest = read(manifest_path)
    verification = read(directory/'verification.json')
    assert verification['manifest_sha256'] == sha(manifest_path)
    if name == 'sacks':
        assert verification['verifier_sha256'] == sha(ROOT/'Tools/lowtide_sack_verify.py')
    else:
        reviewer = 'lowtide_water_filter_review.py' if name == 'water-filter-gentle' else 'lowtide_paving_use_review.py'
        assert verification['reviewer_sha256'] == sha(ROOT/'Tools'/reviewer)
    for relative, expected in manifest['sources'].items():
        assert sha(ROOT/relative) == expected, relative
    for relative, expected in manifest['protected'].items():
        assert sha(ROOT/relative) == expected, relative
        assert protected.get(relative, expected) == expected, relative
        protected[relative] = expected
    staged = manifest.get('staged_files', {p:v['after'] for p,v in manifest.get('changes', {}).items()})
    assert all(sha(directory/'stage'/p) == expected for p, expected in staged.items())
    records[name] = dict(manifest=manifest_path.relative_to(ROOT).as_posix(), manifest_sha256=sha(manifest_path),
                         verification_sha256=sha(directory/'verification.json'), staged_files=len(staged), native_accepted=False)
    if name != 'sacks':
        assert Path(manifest['project_root']).resolve() == ROOT
        preview = read(directory/'preview/provenance.json')
        assert preview['manifest_sha256'] == sha(manifest_path)
        assert len(preview['files']) == 6
        assert all(sha(directory/'preview'/p) == expected for p, expected in preview['files'].items())
        records[name]['preview_provenance_sha256'] = sha(directory/'preview/provenance.json')

water = OUT/'water-filter-gentle'
compile_check = read(water/'compile-verification.json')
assert compile_check['manifest_sha256'] == records['water-filter-gentle']['manifest_sha256']
assert compile_check['warnings'] == compile_check['errors'] == 0
assert all(sha(water/p) == h for p, h in compile_check['files'].items())
assert all(sha(Path(p)) == h for p, h in compile_check['reference_files'].items())
assert read(water/'manifest.json') == read(water/'reproduction/manifest.json')
assert all(sha(water/'stage'/p) == sha(water/'reproduction/stage'/p)
           for p in read(water/'manifest.json')['staged_files'])
records['water-filter-gentle'].update(compile_verification_sha256=sha(water/'compile-verification.json'),
    reproduction_verification_sha256=sha(water/'reproduction-verification.json'),
    visual_review_sha256=sha(water/'visual-review.json'), filter_strength=.08, material_base_roughness=.22)

paving = OUT/'paving-use'
current = read(paving/'manifest.json')
previous = read(ROOT/'output/lowtide/quality-pass/paving-use/manifest.json')
assert all(current[k] == previous[k] for k in ('ground', 'wall_segments', 'drains'))
same = [p for p,h in current['staged_files'].items() if h == previous['staged_files'].get(p)]
changed = [p for p in current['staged_files'] if p not in same]
assert len(same) == 4 and changed == ['shaders/hc1_lowtide_paving_use.shader']
base_shader = (ROOT/'Assets/shaders/hc1_lowtide_paving_relief.shader').read_text()
candidate = (paving/'stage'/changed[0]).read_text()
wetness = base_shader.split('    float PavingWetness(', 1)[1].split('\n    }', 1)[0]
assert candidate.split('    float PavingWetness(', 1)[1].split('\n    }', 1)[0] == wetness
(paving/'shader-change.diff').write_text(''.join(difflib.unified_diff(base_shader.splitlines(True), candidate.splitlines(True),
    fromfile='Assets/shaders/hc1_lowtide_paving_relief.shader', tofile='staged/shaders/hc1_lowtide_paving_use.shader')), encoding='utf-8')
write(paving/'rebase-verification.json', dict(status='current_wetness_preserved_with_reviewed_contact_layout',
    manifest_sha256=sha(paving/'manifest.json'), unchanged_ground_wall_and_outlet_layout=True,
    byte_identical_rebuilt_files=same, changed_files=changed, current_wetness_function_preserved=True,
    native_accepted=False))
records['paving-use']['rebase_verification_sha256'] = sha(paving/'rebase-verification.json')
assert read(paving/'visual-review.json')['manifest_sha256'] == records['paving-use']['manifest_sha256']
records['paving-use']['visual_review_sha256'] = sha(paving/'visual-review.json')

lod_path = OUT/'sack-lods/manifest.json'
if lod_path.is_file():
    lod = read(lod_path)
    checked = read(lod_path.parent/'verification.json')
    proof = read(lod_path.parent/'rebase-verification.json')
    assert Path(lod['project_root']).resolve() == ROOT
    assert checked['manifest_sha256'] == proof['manifest_sha256'] == sha(lod_path)
    assert checked['reviewer_sha256'] == sha(ROOT/'Tools/lowtide_sack_lod_review.py')
    assert proof['verification_sha256'] == sha(lod_path.parent/'verification.json')
    assert lod['baseline_manifest_sha256'] == records['sacks']['manifest_sha256']
    assert all(sha(ROOT/p) == h for p,h in lod['sources'].items())
    for relative, expected in lod['protected'].items():
        assert sha(ROOT/relative) == expected
        assert protected.get(relative, expected) == expected
        protected[relative] = expected
    for models in lod['levels'].values():
        for entry in models.values():
            assert sha(ROOT/entry['component']) == entry['component_sha256']
            assert sha(ROOT/entry['staged']) == entry['staged_sha256']
    for relative, entry in lod['material_libraries'].items():
        assert sha(ROOT/relative) == sha(ROOT/entry['source']) == entry['sha256']
    records['sack-lods'] = dict(manifest=lod_path.relative_to(ROOT).as_posix(), manifest_sha256=sha(lod_path),
        verification_sha256=sha(lod_path.parent/'verification.json'), rebase_verification_sha256=sha(lod_path.parent/'rebase-verification.json'),
        staged_files=sum(len(models) for models in lod['levels'].values())+len(lod['material_libraries']),
        full_aggregate_triangle_counts=proof['full_aggregate_triangle_counts'], native_switching_configured=False, native_accepted=False)

report = dict(status='scoped_offline_candidates_verified', candidate_count=len(records), observed_utc=datetime.now(timezone.utc).isoformat(),
    project_root=str(ROOT), user_work_mode='offline', live_assets_or_code_changed=False,
    protected_live_files=len([p for p in protected if p.startswith(('Assets/', 'Code/'))]),
    protected=protected, candidates=records, native_accepted=False, overall_AAA_verified=False,
    note='This validates the named staged candidates only. Historical candidate bundles have not been globally revalidated.',
    remaining=['Sack distance candidates still require native grouping, switching and performance review.' if 'sack-lods' in records
               else 'Rebase the sack distance alternatives against the current dressing/fleet files.',
               'Revalidate remaining construction, drainage, floor and foliage integration against the canonical checkout.',
               'Native shader/model compilation, scene appearance, temporal behavior, gameplay performance and persistence remain unverified.'])
write(OUT/'scoped-validation.json', report)
status_path = ROOT/'Sources/Lowtide/construction/checkout-status.json'
status = {k:v for k,v in report.items() if k != 'protected'}
status['evidence'] = (OUT/'scoped-validation.json').relative_to(ROOT).as_posix()
status['initial_audit'] = (OUT/'audit.json').relative_to(ROOT).as_posix()
write(status_path, status)
for relative in ('Sources/Lowtide/construction/offline-status.json', 'Sources/Lowtide/sacks/construction-status.json',
                 'Sources/Lowtide/water/filter-status.json', 'Sources/Lowtide/paving/use-status.json', 'Sources/Lowtide/sacks/lod-status.json'):
    path = ROOT/relative
    original = path.read_bytes()
    data = json.loads(original)
    data['latest_checkout_revalidation'] = status_path.relative_to(ROOT).as_posix()
    data['historical_evidence_note'] = 'Other validation fields describe the dated candidate; use latest_checkout_revalidation for the current scoped rebase.'
    # Other validation fields describe their dated historical candidate.
    assert path.read_bytes() == original
    write(path, data)
print(json.dumps({k:v for k,v in status.items() if k != 'candidates'}, indent=2))
