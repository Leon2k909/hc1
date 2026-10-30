"""Remove only superseded payloads owned by this pass; preserve the real rollback."""
from pathlib import Path
import json
import shutil

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/collider-detail-v3-20261027'
resolved=OUT.resolve()
removed=[];size=0
for number in range(1,7):
    keep={'before'} if number==2 else {'assets'} if number==6 else set()
    for name in ('assets','before','native-before','generated'):
        if name in keep:continue
        target=OUT/f'stage-v{number}'/name
        if not target.exists():continue
        assert target.resolve().is_relative_to(resolved),target
        assert target.resolve()!=resolved
        total=sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
        shutil.rmtree(target)
        size+=total;removed.append(str(target.relative_to(OUT)))
assert (OUT/'stage-v2/before/models/maps/collider/collider_structure.obj').is_file()
assert (OUT/'stage-v6/assets/models/maps/collider/collider_structure.obj').is_file()
(OUT/'trial-cleanup.json').write_text(json.dumps(dict(removed=removed,bytes_reclaimed=size,
    original_rollback='stage-v2/before',accepted_assets='stage-v6/assets'),indent=2)+'\n')
print(json.dumps(dict(superseded_directories_removed=len(removed),bytes_reclaimed=size,original_rollback_preserved=True)))
