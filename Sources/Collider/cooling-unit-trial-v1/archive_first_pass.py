from pathlib import Path
import shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/cooling-unit'
DEST=OUT/'revisions/first-pass';assert not DEST.exists()
paths=[OUT/n for n in ('after-main.png','render-report.json','render-process.json','verification.json','manifest.json')]
paths.extend(p for p in (ROOT/'Assets/models/props/collider/cooling-unit-trial-v1').iterdir() if p.is_file())
paths.append(Path(__file__).parent/'build.py');records={}
for p in paths:
    rel=Path('evidence')/p.name if p.is_relative_to(OUT) else p.relative_to(ROOT)
    dst=DEST/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    records[rel.as_posix()]=hashlib.sha256(dst.read_bytes()).hexdigest()
(DEST/'archive.json').write_text(json.dumps(records,indent=2)+'\n');print('First pass archived outside Assets.')
