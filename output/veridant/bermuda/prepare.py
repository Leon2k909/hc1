from pathlib import Path
import json, random, math, shutil
import numpy as np

out = Path('output/veridant/bermuda')
source = out / 'source'
resource = 'models/props/shared/veridant_bermuda_lawn_v1'
stage = out / 'stage' / resource
stage.mkdir(parents=True, exist_ok=True)
gltf = json.loads((source / 'grass.gltf').read_text())
buffer = (source / 'grass_bermuda_01.bin').read_bytes()

def accessor(index):
    a = gltf['accessors'][index]
    v = gltf['bufferViews'][a['bufferView']]
    dtype = np.dtype({5126:'<f4', 5123:'<u2', 5125:'<u4'}[a['componentType']])
    columns = {'SCALAR':1, 'VEC2':2, 'VEC3':3}[a['type']]
    return np.ndarray((a['count'], columns), dtype=dtype, buffer=buffer,
                      offset=v.get('byteOffset',0)+a.get('byteOffset',0),
                      strides=(v.get('byteStride',columns*dtype.itemsize),dtype.itemsize)).copy()

tufts = []
for node in gltf['nodes']:
    if '_small_' not in node['name'] and '_medium_' not in node['name']:
        continue
    p = gltf['meshes'][node['mesh']]['primitives'][0]
    a = p['attributes']
    vertices = accessor(a['POSITION']) * 39.3701
    vertices[:,1] -= vertices[:,1].min() + .08
    uv = accessor(a['TEXCOORD_0'])
    uv[:,1] = 1 - uv[:,1]
    tufts.append((vertices,uv,accessor(p['indices']).astype(int).reshape(-1,3)))

rng = random.Random(841)
offset = 1
triangles = 0
with (stage/'bermuda.obj').open('w') as f:
    f.write('o bermuda\nv n\n'.replace('v n\n','')+'vn 0 1 0\n')
    for east in range(665,1177,2):
        for north in range(-1345,-1224,2):
            if rng.random() < .12:
                continue
            verts, uv, faces = rng.choice(tufts)
            angle = rng.uniform(0, math.tau)
            c,s = math.cos(angle),math.sin(angle)
            x,z = 920-east+rng.uniform(-.85,.85),1285+north+rng.uniform(-.85,.85)
            scale = rng.uniform(.8,1.17)
            for a,b,d in verts:
                f.write(f'v {x+(a*c-d*s)*scale:.4f} {b*scale:.4f} {z+(a*s+d*c)*scale:.4f}\n')
            for u,v in uv:
                f.write(f'vt {u:.6f} {v:.6f}\n')
            for face in faces:
                f.write('f '+' '.join(f'{i+offset}/{i+offset}/1' for i in face)+'\n')
            offset += len(verts)
            triangles += len(faces)

shutil.copyfile(source/'alpha.png',stage/'alpha.png')
shutil.copyfile(source/'textures/grass_bermuda_01_diff_2k.jpg',stage/'diffuse.jpg')
material = Path('Assets/materials/veridant/vr_foliage.vmat').read_text()
material = material.replace('materials/veridant/vr_foliage_trans.png',resource+'/alpha.png').replace('materials/veridant/vr_foliage_color.png',resource+'/diffuse.jpg')
material = material.replace('F_SPECULAR "1"','F_SPECULAR "1"\n    F_RENDER_BACKFACES "1"\n    F_DO_NOT_CAST_SHADOWS "1"')
(stage/'bermuda.vmat').write_text(material)
old = 'models/props/shared/veridant_short_garden_grass_v2'
model = Path('Assets',old,'grass.vmdl').read_text().replace(old+'/grass.vmat',resource+'/bermuda.vmat').replace(old+'/grass_lod0.obj',resource+'/bermuda.obj')
(stage/'bermuda.vmdl').write_text(model)
previous = Path('output/veridant/garden-grass-blades-v2')
script = json.loads((previous/'import.json').read_text())['path']
import_code = Path(script).read_text().replace('garden-grass-blades-v2/stage','bermuda/stage')
exchange = Path(script).with_name('import-bermuda.cs')
exchange.write_text(import_code)
(out/'import.json').write_text(json.dumps({'path':str(exchange)}))
(out/'compile.json').write_text(json.dumps({'path':resource+'/bermuda.vmdl','full':False}))
apply = json.loads((previous/'shade-override.json').read_text())['code'].split('var m=Material.Load')[0]
apply += f'var m=Model.Load("{resource}/bermuda.vmdl");if(m.IsError)throw new Exception("Bermuda model failed");r.Model=m;r.MaterialOverride=null;return r.Model.ResourcePath;'
(out/'apply.json').write_text(json.dumps({'code':apply}))
print(triangles, 'triangles')
