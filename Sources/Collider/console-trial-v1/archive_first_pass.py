from pathlib import Path
import shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/console'
DEST=OUT/'revisions/first-pass';assert not DEST.exists()
paths=[OUT/name for name in ('after-main.png','render-report.json','render-process.json','verification.json','manifest.json')]
for part in ('models/props','materials'):
    paths.extend(p for p in (ROOT/'Assets'/part/'collider/console-trial-v1').iterdir() if p.is_file())
paths.append(Path(__file__).parent/'build.py')
records={}
for src in paths:
    rel=src.relative_to(ROOT) if not src.is_relative_to(OUT) else Path('evidence')/src.name
    dst=DEST/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    records[rel.as_posix()]=hashlib.sha256(dst.read_bytes()).hexdigest()
(DEST/'archive.json').write_text(json.dumps(records,indent=2)+'\n');print('Archived '+str(len(records))+' owned proposal files outside Assets.')
