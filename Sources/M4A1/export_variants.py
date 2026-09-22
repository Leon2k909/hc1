"""Keep the first-person rail vents open; the world asset needs an inner cover.
Uses the baked mesh and UVs without rebaking or changing the authored atlases.
"""
import bpy, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'Assets/attachments/m4a1/heavy_barrel'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Sources/M4A1/m4a1_parts_pbr.blend'))
obj=bpy.data.objects['heavy_barrel'];mesh=obj.data
adj=[set() for v in mesh.vertices]
for e in mesh.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
seen=set();hidden=set()
for start in range(len(adj)):
    if start in seen:continue
    group={start};stack=[start];seen.add(start)
    while stack:
        for other in adj[stack.pop()]:
            if other not in seen:seen.add(other);group.add(other);stack.append(other)
    coords=[mesh.vertices[i].co for i in group]
    ext=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
    if 6.5<ext[0]<6.6 and ext[1]<.03 and 1.19<ext[2]<1.21:hidden.update(group)
assert hidden, 'World liner geometry not found'
mesh.calc_loop_triangles();normals=mesh.corner_normals;uvs=mesh.uv_layers.active.data
for world in [False,True]:
    name='heavy_barrel_world' if world else 'heavy_barrel'
    lines=['mtllib heavy_barrel.mtl',f'o {name}','usemtl heavy_barrel_pbr'];index=1;count=0
    for tri in mesh.loop_triangles:
        if not world and any(v in hidden for v in tri.vertices):continue
        count+=1
        for li in tri.loops:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;n=normals[li].vector;uv=uvs[li].uv
            lines.extend([f'v {v.y:.7f} {v.z:.7f} {v.x:.7f}',f'vt {uv.x:.7f} {uv.y:.7f}',f'vn {n.y:.7f} {n.z:.7f} {n.x:.7f}'])
        lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(index,index+3)));index+=3
    (folder/f'{name}.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
    if world:
        data=(folder/'heavy_barrel.vmdl').read_text(encoding='utf8').replace('/heavy_barrel.obj','/heavy_barrel_world.obj')
        (folder/f'{name}.vmdl').write_text(data,encoding='utf8')
    print(name,count,'triangles')
