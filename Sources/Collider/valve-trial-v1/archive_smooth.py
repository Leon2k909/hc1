"""Preserve the exact proposal the user found too smooth, for a fair revision view."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/asset-improvement-20261029/valve'
ARCHIVE=OUT/'revisions/smooth-v1'
if (ARCHIVE/'archive.json').exists():
    print('Smooth proposal already archived.')
    raise SystemExit(0)
review=json.loads((ROOT/'Sources/Collider/valve-trial-v1/review.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in review['materialSourceSHA256'].items():assert sha(ROOT/p)==h,p
for name,h in review['modelSourceSHA256'].items():assert sha(ROOT/f'Assets/models/props/collider/valve-trial-v1/{name}.obj')==h
paths=list((ROOT/'Assets/materials/collider/valve-trial-v1').glob('*.png'))+list((ROOT/'Assets/materials/collider/valve-trial-v1').glob('*.vmat'))
paths+=list((ROOT/'Assets/models/props/collider/valve-trial-v1').glob('*.obj'))+list((ROOT/'Assets/models/props/collider/valve-trial-v1').glob('*.mtl'))+list((ROOT/'Assets/models/props/collider/valve-trial-v1').glob('*.vmdl'))
paths+=[ROOT/'Sources/Collider/valve-trial-v1'/n for n in ('build.py','candidate.json','review.json')]
records={}
for p in paths:
    rel=p.relative_to(ROOT);target=ARCHIVE/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);records[rel.as_posix()]=sha(p)
for name in ('after-main.png','before-main.png','render-report.json','manifest.json','verification.json'):
    target=ARCHIVE/name;shutil.copyfile(OUT/name,target);records[name]=sha(target)
(ARCHIVE/'archive.json').write_text(json.dumps({'reason':'User found the first proposal too smooth','editorUsed':False,'files':records},indent=2)+'\n')
print('Archived smooth proposal, source resources and matched render.')
