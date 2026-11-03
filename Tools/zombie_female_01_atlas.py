"""Rebuild the scan's UV atlas after decimation, avoiding stretched mipmapped chart borders.

Run in Blender: blender -b --python Tools/zombie_female_01_atlas.py.
Writes work files only; rig --write --meshes-only and textures install them afterwards.
"""
import sys
from pathlib import Path
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import zombie_female_01_blender as export

work = Path('D:/tmp/hc1-mw22-tools/zombie_female_01_work')
bpy.ops.wm.open_mainfile(filepath=str(work/'lods.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 4
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
high = next(o for o in scene.objects if o.type=='MESH' and o.name not in ('lod0','lod1','lod2'))
low = bpy.data.objects['lod0']
for name in ['lod1','lod2']:
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
bpy.ops.object.select_all(action='DESELECT')
low.select_set(True)
bpy.context.view_layer.objects.active=low
# Preserve the existing body/hair UVs in the lower half. Give the visible face a continuous
# planar chart in the upper half, where simplification cannot produce erratic UV derivatives.
mesh=low.data
uv=mesh.uv_layers.active.data
source_uv=np.array([x.uv[:] for x in uv])
sample=bpy.data.images.load(str(work/'base_color.jpg'),check_existing=False)
sample.scale(1024,1024)
pixels=np.array(sample.pixels[:],dtype=np.float32).reshape(1024,1024,4)
col=pixels[(np.clip(source_uv[:,1],0,1)*1023).astype(int),
           (np.clip(source_uv[:,0],0,1)*1023).astype(int),:3]
face_count=0
for p in mesh.polygons:
    c=np.mean([mesh.vertices[v].co[:] for v in p.vertices],axis=0)
    color=np.mean(col[list(p.loop_indices)],axis=0)
    ellipse=((c[0]-(0.045+0.17*(c[2]-1.73)))/0.088)**2+((c[2]-1.738)/0.115)**2
    eye=(1.727<c[2]<1.795 and -0.018<c[0]<0.108)
    skin=color.mean()>0.045 or color[0]-color[2]>0.008
    # The open mouth contains several surfaces along a front ray. Keep its original separate
    # charts so tongue/inner-mouth texels cannot overwrite the lips in the planar chart.
    mouth=1.645<c[2]<1.714 and -0.035<c[0]<0.110
    face=ellipse<1 and c[1]<-0.045 and p.normal.y<-0.05 and (skin or eye) and not mouth
    face_count+=face
    for k in p.loop_indices:
        v=mesh.vertices[mesh.loops[k].vertex_index].co
        uv[k].uv=((v.x+0.06)/0.22,0.53+(v.z-1.60)/0.28*0.45) if face else (source_uv[k,0],source_uv[k,1]*0.47)
print('Continuous face chart:',face_count,'triangles',flush=True)

target=bpy.data.materials.new('atlas_bake_target')
target.use_nodes=True
node=target.node_tree.nodes.new('ShaderNodeTexImage')
target.node_tree.nodes.active=node
mesh.materials.clear()
mesh.materials.append(target)
bake=scene.render.bake
bake.use_selected_to_active=True
bake.cage_extrusion=export.CAGE_EXTRUSION
bake.max_ray_distance=export.MAX_RAY
bake.margin=24
bake.margin_type='EXTEND'
bake.use_pass_direct=False
bake.use_pass_indirect=False
bake.use_pass_color=True
bpy.ops.object.select_all(action='DESELECT')
high.select_set(True)
low.select_set(True)
bpy.context.view_layer.objects.active=low
for name,kind,size in [('atlas_color','DIFFUSE',4096),('atlas_normal','NORMAL',2048),('atlas_rough','ROUGHNESS',2048)]:
    image=bpy.data.images.new(name,size,size,float_buffer=True)
    image.colorspace_settings.name='sRGB' if kind=='DIFFUSE' else 'Non-Color'
    node.image=image
    bpy.ops.object.bake(type=kind)
    image.filepath_raw=str(work/f'{name}.png')
    image.file_format='PNG'
    image.save()
    print('BAKED',name,flush=True)

previous=low
for i,budget in enumerate(export.LODS):
    ob=low if i==0 else export.decimated(previous,budget,f'lod{i}')
    co,tris,uvs,nrm=export.mesh_arrays(ob)
    np.savez(work/f'atlas_lod{i}.npz',positions=co,triangles=tris,uvs=uvs,normals=nrm)
    previous=ob
    print('EXPORTED',i,len(tris),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(work/'atlas_lods.blend'))
