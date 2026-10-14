"""Stage the scoped slate response change; never writes live assets."""
from pathlib import Path
import sys
import shutil
import hashlib
import json
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools'))
import lowtide_roofs as R
folder=Path(__file__).resolve().parent
stage=folder/'roof-response-stage'
before=folder/'roof-response-before'
live=root/'Assets'
R.K.ASSETS=stage
R.DIRECTORY=stage/'materials/lowtide/roofs'
R.bake(R.SOURCE)
R.write_materials()
shader=stage/'shaders/hc1_slate.shader'
R.metadata(shader)
changed=['materials/lowtide/roofs/'+name for name in
         ('slate_normal.png','slate_ao.png','slate_ao.png.meta','lt_slate.vmat')]
changed+=['shaders/hc1_slate.shader','shaders/hc1_slate.shader.meta']
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
changes={}
for relative in changed:
    source=live/relative
    if source.exists():
        dest=before/relative
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(source,dest)
    changes[relative]={'before':digest(source) if source.exists() else None,'after':digest(stage/relative)}
protected={}
for p in (live/'models/maps/lowtide').iterdir():
    if p.suffix in ('.obj','.mtl','.vmdl'):protected[str(p.relative_to(root))]=digest(p)
for relative in ('Assets/scenes/maps/lowtide/lowtide.scene','Assets/materials/lowtide/roofs/slate_color.png',
                 'Assets/materials/lowtide/roofs/slate_rough.png','Sources/Lowtide/visual-target/slate-source.png'):
    protected[relative]=digest(root/relative)
assert digest(stage/'materials/lowtide/roofs/slate_color.png')==digest(live/'materials/lowtide/roofs/slate_color.png')
assert digest(stage/'materials/lowtide/roofs/slate_rough.png')==digest(live/'materials/lowtide/roofs/slate_rough.png')
(folder/'roof-response-manifest.json').write_text(json.dumps({'changes':changes,'protected':protected},indent=2)+'\n')
print(json.dumps({'staged':len(changed),'protected':len(protected),'albedo_preserved':True}))
