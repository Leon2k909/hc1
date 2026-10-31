"""Record the approved, verified offline integration without rewriting review evidence."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = ROOT / 'output/collider-pump-skid-accepted-20261030'
REVIEW = ROOT / 'output/asset-improvement-20261030/pump-skid'
d = json.loads((OUT / 'installed.json').read_text())
v = json.loads((OUT / 'verification.json').read_text())
assert d['userApproved'] and v['approvedPumpInstalled']
assert v['fullPhysicsUnchanged'] and v['sourceGeneratorMatchesExactly']
for p in (HERE / 'candidate.json', HERE / 'review.json', REVIEW / 'manifest.json',
          REVIEW / 'review.json', REVIEW / 'clean-finish-review/review.json'):
    if not p.exists():
        continue
    record = json.loads(p.read_text())
    assert record['realismRevision'] == 4, str(p)
    if 'geometryVerification' in record:
        record['preInstallationGeometryVerification'] = record.pop('geometryVerification')
    record.update(status=d['status'], userApproved=True, installedInMap=True,
                  originalRetained=False, originalArchivedOutsideAssets=True,
                  editorUsed=False, engineCompilation='pending',
                  installationReceipt='Sources/Collider/pump-skid-trial-v1/installed.json',
                  installationVerification=v)
    p.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'acceptedRevision': 4, 'installedInMapSources': True,
                  'verificationPassed': True, 'editorUsed': False, 'engineCompilation': 'pending'}))
