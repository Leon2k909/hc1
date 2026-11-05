"""Extract the published sign and create an isolated context copy. No live writes."""
from pathlib import Path
import hashlib,json,math,re,shutil,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve()
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
OUT=ROOT/'output/asset-improvement-20261030/riverside-speed-sign'
ASSET=ROOT/'Assets/models/props/riverside/speed_sign_v2/review'
ASSET.mkdir(parents=True,exist_ok=True)
base=np.array((-30,85,96),float)
f=np.array((-1,-.4,0));f/=np.linalg.norm(f)
left=np.cross((0,0,1),f)
axes=np.array((f,left,(0,0,1))).T
path=ROOT/'Assets/models/maps/riverside/riverside_pad.obj'
text=path.read_text();points=[];material=None;faces=[];keep=[]
for line in text.splitlines(keepends=True):
    p=line.split();cut=False
    if p and p[0]=='v':points.append(np.array((float(p[3]),float(p[1]),float(p[2]))))
    if p and p[0]=='usemtl':material=p[1]
    if p and p[0]=='f' and material in ('rs_signs','rs_steel'):
        v=(np.array([points[int(t.split('/')[0])-1] for t in p[1:]])-base)@axes
        cut=(abs(v[:,0]).max()<2.2 and abs(v[:,1]).max()<15.1 and v[:,2].min()>-.01 and v[:,2].max()<110.01)
    if cut:faces.append((material,line))
    else:keep.append(line)
assert len(faces)==16,(len(faces),[(m,l) for m,l in faces])
# Keep published UVs/normals and translate its exact geometry into canonical local coordinates.
lines=['mtllib riverside_pad.mtl\n']
for line in text.splitlines(keepends=True):
    p=line.split()
    if not p:continue
    if p[0] in ('v','vn'):
        v=np.array((float(p[3]),float(p[1]),float(p[2])))
        v=(v-base if p[0]=='v' else v)@axes
        lines.append(f'{p[0]} {v[1]:.6f} {v[2]:.6f} {v[0]:.6f}\n')
    elif p[0]=='vt':lines.append(line)
for m,l in faces:lines.extend([f'usemtl {m}\n',l])
(ASSET/'original.obj').write_text(''.join(lines))
(ASSET/'pad_without_sign.obj').write_text(''.join(keep))
shutil.copyfile(path.with_suffix('.mtl'),ASSET/'riverside_pad.mtl')
vmdl=path.with_suffix('.vmdl').read_text()
remaps=re.findall(r'\{\s*from\s*=\s*"[^"]+"\s+to\s*=\s*"[^"]+"\s*\}',vmdl)
assert remaps
for name in ('original','pad_without_sign'):
    (ASSET/(name+'.vmdl')).write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [%REMAPS%] use_global_default = false global_default_material = "" } ] },
{ _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" name = "review" filename = "models/props/riverside/speed_sign_v2/review/%NAME%.obj"
import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1
align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
import_filter = { exclude_by_default = false exception_list = [] } } ] } ] } }
'''.replace('%REMAPS%',','.join(remaps)).replace('%NAME%',name))
protected=[path,path.with_suffix('.vmdl'),ROOT/'Assets/scenes/maps/Riverside/riverside.scene']
manifest=dict(position=base.tolist(),yaw=math.degrees(math.atan2(f[1],f[0])),old_triangles=len(faces),
              protected={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
(OUT/'review.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
