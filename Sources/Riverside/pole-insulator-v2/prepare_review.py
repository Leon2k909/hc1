"""A private comparison of one crossarm insulator; preserve the actual wire."""
from pathlib import Path
import hashlib,json,re,shutil,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_parts as P
import riverside_map as M
OUT=ROOT/'output/asset-improvement-20261030/riverside-pole-insulator'
ASSET=ROOT/'Assets/models/props/riverside/pole_insulator_v2/review';ASSET.mkdir(parents=True,exist_ok=True)
taps,_=P.pole(K.Model(),M.POLES_WEST[2],430,facing=(1,.1),arms=2,seed=2)
base=K.to_world(taps[0])-np.array((0,0,5))
path=ROOT/'Assets/models/maps/riverside/riverside_dressing.obj'
original=path.read_bytes();points=[];material=None;kept=[];removed=[]
for line in original.decode().splitlines(keepends=True):
    p=line.split();cut=False
    if p and p[0]=='v':points.append(np.array((float(p[3]),float(p[1]),float(p[2]))))
    if p and p[0]=='usemtl':material=p[1]
    if p and p[0]=='f' and material=='rs_glass':
        v=np.array([points[int(t.split('/')[0])-1] for t in p[1:]])-base
        cut=(abs(v[:,0]).max()<1.41 and abs(v[:,1]).max()<1.41 and v[:,2].min()>-.01 and v[:,2].max()<5.01)
    (removed if cut else kept).append(line)
assert len(removed)==16,len(removed)
(ASSET/'dressing_without_insulator.obj').write_bytes(''.join(kept).encode())
shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_dressing.mtl')
text=path.with_suffix('.vmdl').read_text();remaps=re.findall(r'\{\s*from\s*=\s*"[^"]+"\s+to\s*=\s*"[^"]+"\s*\}',text)
background='models/props/riverside/pole_insulator_v2/review/dressing_without_insulator.vmdl'
(ROOT/'Assets'/background).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [%REMAPS%] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" name = "background" filename = "models/props/riverside/pole_insulator_v2/review/dressing_without_insulator.obj"
import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1
align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
import_filter = { exclude_by_default = false exception_list = [] } } ] } ] } }
'''.replace('%REMAPS%',','.join(remaps)))
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
manifest=dict(position=base.tolist(),yaw=0,old_triangles=16,wire_contact=(base+np.array((0,0,5))).tolist(),background=background,
              protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
