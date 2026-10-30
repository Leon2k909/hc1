"""Remove only the explicit native exchange directories created for this review."""
import json
import os
from pathlib import Path
import re
import shutil

base = (Path(os.environ['LOCALAPPDATA']) / 'Temp/sbox-cli').resolve()
out = Path(__file__).resolve().parent
identifiers = '''149085ee59984148bf5ce516051d30bc 0a96fdabaa4e46dda3c599e96c27cd1f
307183a2e35941d88e52023c5dac64ca 464885a892a64f0993ac5bc65ef30225
67c409904de04a2891f20e8dd56c2c5a 79d70b33fb7c4c0db528f127c2c27a0d
97205f3ac31d4c1da2f0061c754e204c b0828d84a6624308b778e623e11fce15
c617cc0d3fc341a58bd2f37e04161403 ca2d559406504e21bfbbc48438449f30
d43d17b9e4de45069a8c809f7570520f fe62313b616f40d99edc4f9c7b152bad
2f37c01041384311b57cb83455644e21 1a8940b2ba7247ac900c28abd7933595
9ea6e7e4852040dda86729f7457d44a4 ada8dba68c554361a9b91d8c70606f0a
d26ba4e971c74a2c90c548a7f92f63a3'''.split()
allowed = {'audit.cs', 'bake.cs', 'capture.cs', 'verify.cs', 'install.cs', 'request.json',
           'editor_camera_screenshot-20261027-001635-1.png'}
deleted = []
for ident in identifiers:
    assert re.fullmatch('[a-f0-9]{32}', ident)
    target = base / ident
    if not target.exists():
        continue
    assert not target.is_junction() and not target.is_symlink()
    target = target.resolve()
    assert target.parent == base and target.name == ident
    children = list(target.iterdir())
    assert all(p.is_file() and not p.is_symlink() and p.name in allowed for p in children), str(target)
    for p in children:
        if p.suffix == '.png':
            shutil.copyfile(p, out / 'initial-editor-context.png')
    shutil.rmtree(target)
    deleted.append(str(target))
(out / 'cleanup.json').write_text(json.dumps({'removed_exchange_directories': deleted}, indent=2))
print(json.dumps({'removed_task_exchange_directories': len(deleted)}))
