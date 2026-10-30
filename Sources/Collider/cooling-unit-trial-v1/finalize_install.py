from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/collider-cooling-unit-accepted-20261030'
d=json.loads((OUT/'installed.json').read_text());v=json.loads((OUT/'verification.json').read_text())
assert v['approvedCoolingUnitInstalled'] and v['oldCoolingUnitTrianglesRemaining']==0
for path in (HERE/'review.json',ROOT/'output/asset-improvement-20261030/cooling-unit/review.json'):
    r=json.loads(path.read_text());r.update(status=d['status'],userApproved=True,installedInMap=True,
        oldAssetRetained=False,oldAssetRollbackOutsideAssets=True,
        installationReceipt='Sources/Collider/cooling-unit-trial-v1/installed.json',installationVerification=v)
    path.write_text(json.dumps(r,indent=2)+'\n')
print('Recorded approved cooling-unit installation.')
