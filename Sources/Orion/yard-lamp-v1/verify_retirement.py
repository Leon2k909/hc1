from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
receipt=json.loads((HERE/'retirement/retirement.json').read_text())
plan=json.loads((ROOT/'output/orion/yard-lamp-v1/install-plan.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel,item in receipt.items():
 assert not (ROOT/rel).exists(),rel
 assert sha(ROOT/item['Archive'])==item['Sha256'],rel
for rel,expected in plan['files'].items():assert sha(ROOT/rel)==expected,rel
assert not list((ROOT/'Assets/models/maps/orion/yard-lamp-v1').glob('before.*'))
report=dict(OldFilesRemoved=len(receipt),NewLampInstalledHashesMatch=True,RetiredCopiesVerified=True)
(HERE/'retirement/verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
