"""Verify native adoption and canonical regeneration without touching live assets."""
from pathlib import Path
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT / 'output/lowtide/quality-pass/container-surface'
sys.path.insert(0, str(ROOT / 'Tools'))
import lowtide_container as container

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = json.loads((FOLDER / 'production-manifest.json').read_text())
native = json.loads((FOLDER / 'production-native-verify.json').read_text())
compile_report = json.loads((FOLDER / 'production-compile.json').read_text())
for relative, item in manifest['changes'].items():
    assert digest(ROOT / 'Assets' / relative) == item['after'], relative
    assert native['materialHashes'][relative] == item['after'], relative
    assert compile_report['results'][relative], relative
for relative, expected in manifest['protected'].items():
    assert digest(ROOT / relative) == expected, relative
assert len(native['slots']) == 8 and len(native['bindingChecks']) == 6
assert len(native['captures']) == 4
assert not native['modelErrors'] and not native['materialErrors']
assert not native['HasUnsavedChanges'] and not native['IsPlaying']
assert native['cameraBefore'] == native['cameraAfter']
for capture in native['captures']:
    assert (FOLDER / capture['name']).stat().st_size > 100000

stage = FOLDER / 'canonical-regeneration'
container.K.ASSETS = stage
container.OUT = stage / container.RESOURCE
container.REPORT = FOLDER / 'canonical-report'
container.write_materials()
canonical_files = []
for generated in stage.rglob('*'):
    if not generated.is_file() or generated.name.endswith('.meta'):
        continue
    relative = generated.relative_to(stage)
    assert generated.read_bytes() == (ROOT / 'Assets' / relative).read_bytes(), str(relative)
    canonical_files.append(relative.as_posix())
for name in ('lowtide_container.py', 'lowtide_container_surface.py'):
    ast.parse((ROOT / 'Tools' / name).read_text())
report = {'status': 'passed', 'production_materials': len(manifest['changes']),
          'protected_sources_unchanged': len(manifest['protected']),
          'canonical_files_byte_identical': canonical_files,
          'native_material_slots': len(native['slots']), 'native_captures': len(native['captures']),
          'camera_restored': True,
          'scope': manifest['scope'],
          'limits': 'No controlled gameplay performance comparison. Final screenshots require visual review; whole-map AAA quality is not certified.'}
(FOLDER / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key != 'canonical_files_byte_identical'}))
