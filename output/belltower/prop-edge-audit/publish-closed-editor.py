"""Install this one reviewed mesh only when no editor or compiler is running."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require_closed():
    script = ("Get-CimInstance Win32_Process | Where-Object Name -Match "
              "'^sbox-dev[.]exe$|^resourcecompiler[.]exe$' | "
              "Select-Object ProcessId,Name | ConvertTo-Json -Compress")
    result = subprocess.run(['powershell','-NoProfile','-Command',script],
                            capture_output=True,text=True,check=True)
    if result.stdout.strip():
        raise RuntimeError('Editor or resource compiler is running; leave the live asset unchanged.')


require_closed()
manifest = json.loads((OUT/'stage/manifest.json').read_text())
relative = 'Assets/models/maps/belltower/shop-display-v2/shop_displays.obj'
assert list(manifest['files']) == [relative]
target = (ROOT/relative).resolve()
allowed = (ROOT/'Assets/models/maps/belltower/shop-display-v2').resolve()
assert target.parent == allowed
row = manifest['files'][relative]
source = (ROOT/row['source']).resolve()
backup = (ROOT/row['backup']).resolve()
assert source.is_relative_to(OUT/'stage') and backup.is_relative_to(OUT/'before')
assert sha(source) == row['after'] and sha(backup) == row['before']
for group in ('source_sha256','protected_sha256'):
    for path, expected in manifest[group].items():
        assert sha(ROOT/path) == expected, ('Changed input',path)
current = sha(target)
assert current in (row['before'],row['after']), 'A newer display revision is installed.'
incoming = target.with_name(target.name+'.soft-props-incoming')
assert incoming.parent == allowed and not incoming.exists()
if current != row['after']:
    try:
        shutil.copyfile(source,incoming)
        assert sha(incoming) == row['after'] and sha(target) == row['before']
        require_closed()
        os.replace(incoming,target)
    finally:
        if incoming.exists():
            incoming.unlink()
assert sha(target) == row['after']
record = {
    'source_mesh_installed':True,'publication_mode':'guarded closed-editor atomic replacement',
    'written_asset':relative,'sha256':row['after'],'native_compilation_verified':False,
    'native_map_visual_review_verified':False,'town_meshes_written':[],
    'scene_file_written':False,'materials_or_textures_written':False,
    'new_colliders':0,'editor_launched_or_stopped':False
}
(OUT/'offline-publication.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
