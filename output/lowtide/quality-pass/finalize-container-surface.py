from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
folder = ROOT / 'output/lowtide/quality-pass/container-surface'
verification = json.loads((folder / 'verification.json').read_text())
assert verification['status'] == 'passed'
manifest = json.loads((folder / 'production-manifest.json').read_text())
verification['visual_review'] = 'All four production views reviewed and accepted: modest improvement in enamel response and seam/base weathering; broader art-quality goal remains open.'
verification['limits'] = 'No controlled gameplay performance comparison. Wider architecture and foliage remain below the intended AAA target.'
(folder / 'verification.json').write_text(json.dumps(verification, indent=2) + '\n')
status = {
 'status': 'complete: six production materials compiled, loaded and visually verified',
 'generator': 'Tools/lowtide_container_surface.py',
 'canonical_integration': 'Tools/lowtide_container.py.write_materials',
 'shader_source': 'Sources/Lowtide/containers/hc1_lowtide_container.shader',
 'material_hashes': {relative: item['after'] for relative, item in manifest['changes'].items()},
 'evidence': 'output/lowtide/quality-pass/container-surface/verification.json',
 'native_report': 'output/lowtide/quality-pass/container-surface/production-native-verify.json',
 'changes': 'Intact enamel has smoother roughness, with lower-rail dirt, top-seam runoff and sparse rough dielectric oxide. All existing generated paint pixels and UVs retained.',
 'validation': {'compiled_materials': 6, 'loaded_slots': 8, 'production_views_reviewed': 4,
                'protected_sources_unchanged': 536, 'canonical_files_byte_identical': 22,
                'fresh_native_errors': 0, 'scene_clean': True, 'camera_and_prior_tab_restored': True},
 'do_not_reapply': True,
 'limits': verification['limits']
}
(ROOT / 'Sources/Lowtide/containers/surface-status.json').write_text(json.dumps(status, indent=2) + '\n')

def replace_file(path, text, original):
    assert path.read_bytes() == original
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    temporary = path.with_name(path.name + '.writing')
    temporary.write_bytes(text.encode('utf-8').replace(b'\n', newline))
    temporary.replace(path)

path = ROOT / 'CLAUDE.md'
original = path.read_bytes()
text = original.decode('utf-8').replace('\r\n', '\n')
start = text.index('- Container surface candidate (2026-10-14):')
end = text.index('- Container construction (2026-10-14):', start)
text = text[:start] + '''- Container surface (2026-10-14): the six production materials now use `hc1_lowtide_container.shader`
  for enamel roughness, base dirt, seam runoff and sparse oxide. Existing generated paint textures,
  UVs, geometry, collision, scene and lighting are unchanged. The canonical container generator
  emits the shader/materials; all 22 generated shader/material/texture files match production byte
  for byte. Six material compilations, eight loaded slots and four reviewed production views pass;
  536 protected files match. Camera and prior tab are restored, with no new native errors.
  Evidence: `output/lowtide/quality-pass/container-surface/verification.json` and
  `Sources/Lowtide/containers/surface-status.json`. The candidate import completed after the stall;
  do not rerun it. This is a modest finish improvement, not completion of the overall AAA target.
''' + text[end:]
replace_file(path, text, original)
path = ROOT / 'Sources/Lowtide/visual-target/art-direction.md'
original = path.read_bytes()
text = original.decode('utf-8').replace('\r\n', '\n')
text += '''
The six container materials now use the reviewed enamel shader in production.
Smoother intact paint, rough oxide, seam runoff and base dirt produce a modest
finish improvement across blue, red and grey variants. All existing generated
paint pixels, UVs, geometry, collision, lighting and scene data are retained.
Six materials compile and eight original material slots load correctly without
preview overrides. Four production views are reviewed; 536 protected files match.
The canonical generator reproduces all 22 shader/material/texture files byte for
byte. The camera and prior tab are restored and no new native errors were logged.
Evidence: container-surface/verification.json under the quality-pass folder.
This does not resolve wider architectural repetition or the angular foliage, and
there is no controlled gameplay performance comparison for this material change.
'''
replace_file(path, text, original)
print('Production container surface evidence and documentation finalized.')
