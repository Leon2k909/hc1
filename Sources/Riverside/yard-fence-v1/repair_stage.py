"""Normalize the initial staging name after the template name-order correction."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/yard-fence-v1';stage=OUT/'stage';p=stage/'Assets/models/props/riverside/yard_fence_v1/store_without_fence.vmdl';q=p.with_name('dressing_without_fence.vmdl')
if p.exists():
 q.write_bytes(p.read_bytes());p.unlink()
 m=json.loads((OUT/'manifest.json').read_text());m['files'].pop(p.relative_to(stage).as_posix());m['files'][q.relative_to(stage).as_posix()]=hashlib.sha256(q.read_bytes()).hexdigest();m['background']='models/props/riverside/yard_fence_v1/dressing_without_fence.vmdl';(OUT/'manifest.json').write_text(json.dumps(m,indent=2))
p=Path(__file__).parent/'build.py';p.write_text(p.read_text().replace('store_without_fence','dressing_without_fence'))
