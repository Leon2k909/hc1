"""Create a render-only ice-freezer comparison without editing live map assets."""
from pathlib import Path
import hashlib, json, re, shutil, sys
import numpy as np
ROOT = Path(sys.argv[1]).resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'Tools'))
import riverside_map as M
import map_kit as K
OUT = ROOT / 'output/asset-improvement-20261030/riverside-ice-freezer'
ASSET = ROOT / 'Assets/models/props/riverside/ice_freezer_v2/review'
ASSET.mkdir(parents=True, exist_ok=True)
centre = np.array(K.to_world((M.STORE_DOOR[0]-40, M.STORE[2]-18, M.STORE_FLOOR)))
path = ROOT / 'Assets/models/maps/riverside/riverside_store.obj'
points, material, removed, kept = [], None, [], []
for line in path.read_text().splitlines(keepends=True):
    p = line.split()
    if p and p[0] == 'v':
        # OBJ export axes are Y, Z, X.
        points.append(np.array((float(p[3]), float(p[1]), float(p[2]))))
    if p and p[0] == 'usemtl': material = p[1]
    cut = False
    if p and p[0] == 'f' and material in ('rs_fridge', 'rs_lit'):
        v = np.array([points[int(t.split('/')[0])-1] for t in p[1:]])-centre
        cut = (abs(v[:,0]).max() < 15.3 and abs(v[:,1]).max() < 19.1 and v[:,2].min() >= -.01 and v[:,2].max() <= 60.01)
    if cut: removed.append(line)
    else: kept.append(line)
assert len(removed) == 14, len(removed)
target = ASSET / 'store_without_ice.obj'
target.write_text(''.join(kept))
shutil.copyfile(path.with_suffix('.mtl'), ASSET / 'riverside_store.mtl')
remaps = re.findall(r'\{\s*from\s*=\s*"[^"]+"\s+to\s*=\s*"[^"]+"\s*\}', path.with_suffix('.vmdl').read_text())
assert remaps
model = 'models/props/riverside/ice_freezer_v2/review/store_without_ice.vmdl'
(ROOT / 'Assets' / model).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [%REMAPS%] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" name = "background" filename = "models/props/riverside/ice_freezer_v2/review/store_without_ice.obj"
 import_translation = [0.0,0.0,0.0] import_rotation = [0.0,0.0,0.0] import_scale = 1.0
 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
 parent_bone = "" import_filter = { exclude_by_default = false exception_list = [] }
} ] } ] } }
'''.replace('%REMAPS%', ',\n'.join(remaps)))
protected = [path, path.with_suffix('.vmdl'), ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
manifest = dict(position=centre.tolist(), yaw=180, removed_triangles=len(removed), background=model,
                protected={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
