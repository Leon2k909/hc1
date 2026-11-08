"""Stage exact existing rail panes as independent breakable glass.

Run from the checkout; install plan.json through the native editor script.
Only vr_glass_clear faces leave the aggregate render imports. All original
vertex tables, other faces, materials and physics remain byte-for-byte.
"""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import map_kit as K
from cerroblanco_glass import rotation

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/veridant/breakable-rails-v1/stage'
RESOURCE = 'models/maps/veridant/breakable-rails-v1'


def scene_group():
    """Keep the installed pane objects when the map scene is regenerated."""
    return json.loads((ROOT / 'Sources/Veridant/breakable-rails-v1/group.json').read_text())


def write_static_model(out, resource, name, model):
    """Preview geometry keeps glass; exported map meshes use the separate panes."""
    if name not in ('veridant_buildings', 'veridant_dress'):
        return K.write_model(out, resource, name, model)
    panes = model.polygons.pop('vr_glass_clear', None)
    try:
        return K.write_model(out, resource, name, model)
    finally:
        if panes is not None:
            model.polygons['vr_glass_clear'] = panes


def stage():
    ids = K.SceneIds('afe7902b-538f-4898-aae3-d1c4798e1948')
    children, imports, models = [], [], []
    for aggregate in ('veridant_buildings', 'veridant_dress'):
        document = ROOT / 'Assets/models/maps/veridant' / (aggregate + '.vmdl')
        for relative in re.findall(r'filename = "([^"]+\.obj)"', document.read_text()):
            source = ROOT / 'Assets' / relative
            data = source.read_bytes()
            lines = data.decode().splitlines(keepends=True)
            vertices, uvs, normals, faces, retained = [], [], [], [], []
            paint = None
            for line in lines:
                fields = line.split()
                if fields:
                    if fields[0] == 'v': vertices.append(np.array(list(map(float, fields[1:4])))[[2,0,1]])
                    elif fields[0] == 'vt': uvs.append(tuple(map(float, fields[1:3])))
                    elif fields[0] == 'vn': normals.append(np.array(list(map(float, fields[1:4])))[[2,0,1]])
                    elif fields[0] == 'usemtl': paint = fields[1]
                    elif fields[0] == 'f' and paint == 'vr_glass_clear':
                        faces.append([tuple(int(i)-1 for i in part.split('/')) for part in fields[1:]])
                        continue
                retained.append(line)
            if not faces: continue
            assert len(faces) % 4 == 0, (relative, len(faces))
            target = STAGE / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(''.join(retained).encode())
            imports.append({'source':str(source), 'staged':str(target),
                            'sha256':hashlib.sha256(data).hexdigest(), 'removed':len(faces)})
            for start in range(0, len(faces), 4):
                pane = faces[start:start+4]
                points = np.array([vertices[i] for i in sorted({v[0] for f in pane for v in f})])
                assert len(points) == 8
                centre = points.mean(axis=0)
                normal = normals[pane[0][0][2]].copy()
                normal[2] = 0
                normal /= np.linalg.norm(normal)
                up = np.array([0.,0.,1.])
                across = np.cross(up, normal)
                axes = np.column_stack((normal, across, up))
                local = (points-centre) @ axes
                size = np.ptp(local, axis=0)
                assert .59 < size[0] < .61 and size[1] > 1 and size[2] > 1
                model = K.Model()
                # OBJ is already in engine coordinates; map_kit expects plan coordinates.
                def plan(p): return np.array([-p[1], p[0], p[2]])
                for face in pane:
                    model.polygon('vr_glass_clear', [plan((vertices[v]-centre) @ axes) for v,t,n in face],
                                  normal=plan(normals[face[0][2]] @ axes),
                                  uv=[uvs[t] for v,t,n in face])
                model.hull([plan(p) for p in local], 'glass')
                model.material_overrides['vr_glass_clear'] = 'materials/veridant/vr_glass_clear.vmat'
                model.tile_overrides['vr_glass_clear'] = 64
                name = f'{aggregate}_{start//4:03}'
                K.write_model(STAGE / RESOURCE, RESOURCE, name, model)
                path = f'{RESOURCE}/{name}.vmdl'
                models.append(path)
                key = f'rail/{name}'
                # rotation() expects plan axes and converts them back to engine coordinates.
                orientation = rotation(tuple(plan(axes[:,i]) for i in range(3)))
                children.append(K.game_object(ids, f'Breakable Rail Glass {name}', key, centre,
                    rotation=orientation, tags='glass,navskip', components=[
                        K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=path,RenderType='Off',Tint='1,1,1,1'),
                        K.component(ids,'Sandbox.ModelCollider',key+'/collider',Model=path,Static=True,IsTrigger=False),
                        K.component(ids,'Facepunch.BreakableGlass',key+'/glass',IntactModel=path,
                            BrokenModels=[],PaneSize=K.vec(size[1:]),ShardDensity=14,
                            BreakSound='sounds/buildings/glass_break.sound',
                            ShardEffect={'_type':'gameobject','prefab':'prefabs/buildings/glass_shatter.prefab'})]))
    assert children, 'Already installed, or no rail glass found; do not install an empty group.'
    group = K.game_object(ids, 'Breakable Railing Glass', 'rails', children=children)
    plan = {'imports':imports,'models':models,'group':group}
    STAGE.mkdir(parents=True, exist_ok=True)
    (STAGE/'plan.json').write_text(json.dumps(plan,indent=2))
    print(json.dumps({'panes':len(children),'imports':imports,'plan':str(STAGE/'plan.json')},indent=2))


if __name__ == '__main__': stage()
