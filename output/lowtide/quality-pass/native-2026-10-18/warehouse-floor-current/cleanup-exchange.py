"""Remove only this floor pass's scripts from the native session exchange."""
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[4]
exchange=Path(r'C:\Users\leon2\AppData\Local\Temp\sbox-cli\9b705a7fa05c489fbc772f40a41b8e93').resolve()
names=['import-resources','inspect-resources','register-resources','apply-native-fix','preview',
       'inspect-dressing','inspect-bounds','apply-promotion','capture-production','inspect-bake',
       'rebake-lighting','capture-lighting','store-bake','inspect-prefab-cache','cleanup-bake']
removed=[]
missing=[]
for name in names:
    path=(exchange/('floors-'+name+'.cs')).resolve()
    assert path.parent==exchange and path.suffix=='.cs'
    if path.exists():
        assert path.is_file()
        path.unlink()
        removed.append(path.name)
    else: missing.append(path.name)
(OUT/'exchange-cleanup.json').write_text(json.dumps(dict(removed=removed,alreadyAbsent=missing,otherSessionFilesPreserved=True),indent=2)+'\n')
for relative in ['Sources/Lowtide/floor/floor-status.json','Sources/Lowtide/concrete/wear-status.json',OUT.relative_to(ROOT).as_posix()+'/verification.json']:
    path=ROOT/relative
    data=json.loads(path.read_text())
    data['final_native_readback']=OUT.relative_to(ROOT).as_posix()+'/final-native-readback.json'
    data['exchange_cleanup']=OUT.relative_to(ROOT).as_posix()+'/exchange-cleanup.json'
    path.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(dict(removed=len(removed),alreadyAbsent=len(missing),otherSessionFilesPreserved=True)))
