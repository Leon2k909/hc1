import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
EXCHANGE=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/9b705a7fa05c489fbc772f40a41b8e93')
old=HERE.parent/'warehouse-floor-current'
backup=HERE/'lighting-before';backup.mkdir(exist_ok=True)
paths=['Assets/scenes/maps/Lowtide/lowtide.scene','Sources/Lowtide/lighting/warehouse-lighting.json','Sources/Lowtide/lighting/bake-provenance.json']
hashes={}
for relative in paths:
    path=ROOT/relative;target=backup/path.name
    if target.exists(): assert path.read_bytes()==target.read_bytes(), f'Existing backup differs: {relative}'
    else: shutil.copyfile(path,target)
    hashes[relative]=hashlib.sha256(path.read_bytes()).hexdigest()
(backup/'hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
for source,dest in [('rebake-lighting.cs','structure-v2-rebake.cs'),('store-bake.cs','structure-v2-store.cs')]:
    text=(old/source).read_text().replace('warehouse-floor-current','structure-timber-v2').replace('warehouse-{side}-v4','warehouse-{side}-v5')
    (HERE/source).write_text(text,encoding='utf-8')
    (EXCHANGE/dest).write_text(text,encoding='utf-8')
print(json.dumps({'backups':hashes,'scripts':2},indent=2))
