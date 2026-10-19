from pathlib import Path
import shutil

root=Path(__file__).resolve().parents[4]
out=root/'output/lowtide/quality-pass/concrete-wear'
target=out/'first-review'
assert target.resolve().is_relative_to(out.resolve()) and not target.exists()
target.mkdir()
for name in ('stage','preview'):
    shutil.copytree(out/name,target/name)
for name in ('manifest.json','offline-verification.json'):
    shutil.copy2(out/name,target/name)
for path in (root/'Tools/lowtide_concrete_wear.py',root/'Sources/Lowtide/concrete/wear-layout.json',root/'Sources/Lowtide/concrete/warehouse-use.hlsl'):
    shutil.copy2(path,target/path.name)
print('First floor-use review archived: continuous tire strokes are superseded')
