"""Retire the unreferenced pre-stool base from active Assets, preserving rollback outside Assets."""
from pathlib import Path
import hashlib,json,subprocess,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/veridant/terrace-stools-v1'
relative=(OUT/'source-path.txt').read_text().strip();asset=(ROOT/'Assets'/relative).resolve()
allowed=(ROOT/'Assets/models/maps/veridant/terrace-umbrella-v1/base_without_canopy.obj').resolve()
assert asset==allowed
refs=subprocess.run(['rg','-l','-F',relative,str(ROOT/'Assets'),'-g','*.vmdl','-g','*.prefab','-g','*.scene'],capture_output=True,text=True)
assert refs.returncode==1,(refs.stdout,refs.stderr)
archive=OUT/'retired-old-source';archive.mkdir(parents=True,exist_ok=True)
assert 'terrace-stools-v1' in str(archive.resolve())
receipt=[]
for src in (asset,Path(str(asset)+'.meta')):
    dst=archive/src.name
    if not src.exists():
        assert dst.exists();continue
    if src==asset:assert src.read_bytes()==(OUT/'before/base.obj').read_bytes()
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists():assert dst.read_bytes()==src.read_bytes();src.unlink()
    else:shutil.move(str(src),str(dst))
    receipt.append({'source':str(src),'archived_outside_assets':str(dst),'sha256':digest})
(OUT/'retirement.json').write_text(json.dumps({'no_asset_references':True,'retired':receipt},indent=2));print(json.dumps({'retired_files':len(receipt),'new_stools_remain_active':True}))
