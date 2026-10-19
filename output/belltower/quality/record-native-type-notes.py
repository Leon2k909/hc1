"""Record successful offline API checks without claiming live validation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
report = json.loads((ROOT/'output/belltower/quality/native-script-types/report.json').read_text())
assert report['exit_code'] == 0 and not report['executed']
for path, digest in report['scripts'].items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest
path = ROOT/'CLAUDE.md'
before = path.read_bytes()
text = before.decode('utf-8')
anchor = '    matching valley, west-ridge and terrace views before changing any accepted landscape input or manifest.'
assert text.count(anchor) == 1
addition = '''
    `check-native-script-types.py` type-checks the six garden/canopy/camera method bodies against the installed
    .NET 10 engine assemblies without executing them. `native-script-types/report.json` records the matching
    script hashes and zero compiler diagnostics. This confirms API compatibility, not native rendering or restoration.'''
incoming = path.with_name('CLAUDE.belltower-types.tmp')
assert not incoming.exists()
incoming.write_text(text.replace(anchor, anchor+addition), encoding='utf-8', newline='')
assert path.read_bytes() == before, 'Concurrent CLAUDE edit; inspect before replacing.'
incoming.replace(path)
print('Recorded six passing offline script type checks; native validation remains pending.')
