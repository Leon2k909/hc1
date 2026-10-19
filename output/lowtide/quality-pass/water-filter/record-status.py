"""Bind the reviewed offline water candidate to its compile and reproduction evidence."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


manifest = read(OUT/'manifest.json')
checked = read(OUT/'verification.json')
preview = read(OUT/'preview/provenance.json')
first = read(OUT/'first-review/manifest.json')
digest = sha(OUT/'manifest.json')
assert checked['manifest_sha256'] == preview['manifest_sha256'] == digest
assert sha(OUT/'reproduction/manifest.json') == digest
assert all(sha(ROOT/p) == h for p, h in manifest['sources'].items())
assert all(sha(ROOT/p) == h for p, h in manifest['protected'].items())
assert all(sha(OUT/'stage'/p) == sha(OUT/'reproduction/stage'/p) == h for p, h in manifest['staged_files'].items())
assert all(sha(OUT/'preview'/p) == h for p, h in preview['files'].items())
assert all(sha(Path(p)) == h for p, h in manifest['api']['external_sources'].items())
assert all((sha(ROOT/p) == h if h else not (ROOT/p).exists()) for p, h in manifest['live_before'].items())
code = 'Code/Map/LowtideWaterReflections.cs'
assert first['staged_files'][code] == manifest['staged_files'][code]
for name in ('canal', 'bank', 'reverse'):
    assert sha(OUT/'preview'/f'{name}-before.png') == sha(OUT/'first-review/preview'/f'{name}-before.png')

reproduction = dict(status='byte_identical_offline_stage_passed', manifest_sha256=digest,
                    byte_identical_files=len(manifest['staged_files']), identical_manifest=True,
                    identical_capture_patch=sha(OUT/'capture-change.diff') == sha(OUT/'reproduction/capture-change.diff'),
                    native_compile_or_import=False)
assert reproduction['identical_capture_patch']
write(OUT/'reproduction-verification.json', reproduction)

engine = Path('D:/SteamLibrary/steamapps/common/sbox/bin/managed')
compile_files = ['compile/WaterCheck.csproj', 'compile/NuGet.Config', 'compile/build-output.txt',
                 'compile/bin/Debug/net10.0/LowtideWaterOfflineCheck.dll']
log = (OUT/'compile/build-output.txt').read_text()
assert 'Build succeeded.' in log and '0 Warning(s)' in log and '0 Error(s)' in log
compiled = dict(status='isolated_csharp_api_compile_passed', manifest_sha256=digest,
                source_sha256=manifest['staged_files'][code], source=code,
                files={p:sha(OUT/p) for p in compile_files}, sdk='10.0.202',
                reference_files={(engine/(name+'.dll')).as_posix():sha(engine/(name+'.dll'))
                    for name in ('Sandbox.System', 'Sandbox.Engine', 'Sandbox.Filesystem', 'Sandbox.Reflection', 'Sandbox.Mounting')},
                warnings=0, errors=0, loaded_into_engine=False, shader_compiled=False,
                capture_source_identical_to_first_review_compile=True,
                limitations=['Isolated net10.0 compilation against installed assemblies only',
                             'No s&box sandbox analyzers/source generators, native shader compilation or GPU execution',
                             'Subsequent review changed only shader/material filter strength; compiled C# bytes are identical'])
write(OUT/'compile-verification.json', compiled)

saved = dict(date='2026-10-15', status='offline_candidate_ready_for_native_review',
    revision=manifest['revision'], user_work_mode='Continue offline for now',
    production_changed=False, native_accepted=False, canonical_generator_changed=False,
    generator='Tools/lowtide_water_filter.py', reviewer='Tools/lowtide_water_filter_review.py',
    shader_extension='Sources/Lowtide/water/reflection-filter.hlsl',
    finding='The current planar capture has one mip and always samples level zero, independent of roughness and distorted UV footprint.',
    changes=[
        'Allocate up to seven mips on the existing half-resolution planar target.',
        'Generate the installed linear HDR Box pyramid after the reflection view and before publishing the texture.',
        'Select a continuous mip from roughness and the distorted UV footprint, with a conservative 0.35 roughness-filter scale.',
        'Preserve reflection registration, release, camera guards, water exclusion, view projection, waves, Fresnel, absorption and lighting.',
        'A one-level target clamps to level zero, permitting a safe shader-only fallback during later staged review.'
    ],
    scope=dict(staged_files=4, max_mips=7, roughness_filter_scale=.35,
               delta_triangles=0, new_material_slots=0, extra_water_texture_lookups=0,
               max_downsample_passes=6, additional_color_bytes_at_960x540=1380960,
               memory_note='Colour pyramid allocation only; excludes depth, alignment, pooling and driver overhead.',
               performance='Additional mip generation and trilinear sampling costs are unmeasured.'),
    evidence=dict(manifest='output/lowtide/quality-pass/water-filter/manifest.json', manifest_sha256=digest,
                  verification='output/lowtide/quality-pass/water-filter/verification.json',
                  reproduction='output/lowtide/quality-pass/water-filter/reproduction-verification.json',
                  compile='output/lowtide/quality-pass/water-filter/compile-verification.json',
                  views='output/lowtide/quality-pass/water-filter/preview/provenance.json',
                  protected_live_files_unchanged=560, byte_identical_staged_files=4,
                  isolated_csharp_compile_warnings=0, isolated_csharp_compile_errors=0),
    preview=dict(kind='Six matched synthetic CPU canal views', native_engine_capture=False,
                 actual_lowtide_scene=False,
                 visual_review='Reviewed before/candidate from the canal, bank and reverse direction. Scale 0.35 keeps nearby reflected window/masonry forms readable while reducing fine reflection detail; distance blur still needs engine review.',
                 unchanged_before_images_verified=True,
                 limitations=['Synthetic geometry and approximate optics; no map appearance acceptance',
                              'Box mip filtering approximates a projected roughness footprint; it is not a full GGX convolution or reflection-depth correction',
                              'Native shader, sandbox hotload, GPU barriers, real lighting, temporal AA and performance remain untested']),
    first_review=dict(directory='output/lowtide/quality-pass/water-filter/first-review',
                      roughness_filter_scale=1, rejected=True,
                      reason='Full-strength box filtering removed too much reflected building detail in all three static fixtures.'),
    integration=dict(stage='output/lowtide/quality-pass/water-filter/stage',
                     path_convention='Stage keys are project-relative, including Assets/ and Code/.',
                     code_patch='output/lowtide/quality-pass/water-filter/capture-change.diff',
                     live_target_states=manifest['live_before'],
                     native_followup=[
        'Keep offline mode until the user resumes native work. Start with fresh editor/project/compile/scene/play/unsaved state.',
        'Revalidate the manifest, all live-before hashes and absent targets. Compile the new shader and an unused review material through the editor.',
        'Apply only the scoped capture diff after confirming current C# matches. Do not overwrite later lifecycle changes with the full staged snapshot. Wait for native sandbox compilation and check errors.',
        'Compare in the existing normal viewport. Check single/multiple editor views, gameplay camera, camera changes, detach/reload, reflection exclusion, flip, capture bounds, and fallback water elevations.',
        'Inspect near and distant reflection detail, HDR brightness, bank boundaries, movement stability and GPU cost. The offline images do not establish these results.',
        'After native acceptance, promote only the listed shader/meta/material and code changes. Integrate the selected shader/parameter with Tools/lowtide_water.py without regenerating unrelated scene content.',
        'Save, verify persistence, and retain the previous material/capture behavior if any native lifecycle or performance check fails.'
    ]), overall_goal='Open: map-wide native appearance and gameplay performance are not established')
write(ROOT/'Sources/Lowtide/water/filter-status.json', saved)

status_path = ROOT/'Sources/Lowtide/construction/offline-status.json'
status = read(status_path)
status['separate_pending_work']['water_reflection_filtering'] = 'Sources/Lowtide/water/filter-status.json'
write(status_path, status)

note = '''- Offline water reflection filtering (2026-10-15): `Sources/Lowtide/water/filter-status.json`
  records a separate candidate for the one-mip, level-zero planar reflection path. A bounded
  seven-mip linear HDR Box pyramid supplies roughness/UV-footprint filtering. The reviewed scale
  is 0.35; the first full-strength trial blurred away too much reflected architecture. Existing
  capture lifecycle, camera guards, waves and optics are preserved. Four staged files reproduce
  byte for byte and 560 protected live files are unchanged. Isolated C# API compilation passes
  with no warnings/errors; it is not a sandbox/native shader compile or an engine hotload.
  Six synthetic CPU fixture views are reviewed, not screenshots or map-quality acceptance.
  The 960x540 colour target gains 1,380,960 bytes and up to six downsample passes; actual GPU cost
  is unmeasured. Native appearance, temporal stability, lifecycle, shader compilation and canonical
  integration remain pending. Keep offline mode. Stage keys include Assets/ and Code/; apply the
  scoped capture diff after fresh before-hash checks, never overwrite later code from its snapshot.
'''
notes = ROOT/'CLAUDE.md'
old = notes.read_bytes()
newline = '\r\n' if b'\r\n' in old else '\n'
anchor = '## Lowtide (multiplayer map, `Tools/lowtide_map.py`)'+newline
text = old.decode('utf-8')
if note.splitlines()[0] not in text:
    assert text.count(anchor) == 1
    replacement = text.replace(anchor, anchor+note.replace('\n', newline), 1).encode('utf-8')
    temporary = notes.with_name('CLAUDE.water-filter.tmp')
    assert not temporary.exists()
    temporary.write_bytes(replacement)
    assert notes.read_bytes() == old
    os.replace(temporary, notes)
print(json.dumps(dict(status='water_handoff_recorded', manifest_sha256=digest,
                      staged_files=4, protected=560, isolated_compile='0 warnings, 0 errors',
                      native_accepted=False), indent=2))
