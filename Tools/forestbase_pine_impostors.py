"""Render far-tree impostors from the CC0 authored crown, using cached 1K source maps."""
import bpy, re, math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent.parent
folder=root/'Assets/models/maps/forestbase/pine'
for image in bpy.data.images:
    name=Path(image.filepath).name
    stem=re.sub(r'_[1248]k\.(png|jpg|exr)$','_1k.jpg',name)
    path=folder/'textures'/stem
    if 'twig_alpha' in name: path=folder/'textures/twig_alpha.png'
    if path.is_file(): image.filepath=str(path); image.reload()
for mat in bpy.data.materials:
    source=next((n for n in ('trunk_a','trunk_b','twig','bark') if n in mat.name),'bark')
    path=folder/f'textures/pine_tree_01_{source}_diff_1k.jpg'
    mat.use_nodes=True; mat.node_tree.nodes.clear()
    texture=mat.node_tree.nodes.new('ShaderNodeTexImage'); texture.image=bpy.data.images.load(str(path),check_existing=True)
    shader=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled'); shader.inputs['Roughness'].default_value=.8
    output=mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(texture.outputs['Color'],shader.inputs['Base Color'])
    mat.node_tree.links.new(shader.outputs[0],output.inputs['Surface'])
for o in list(bpy.data.objects):
    if o.type!='MESH' or not o.name.endswith('LOD2'): bpy.data.objects.remove(o,do_unlink=True)
    else:
        o.hide_render=True; o.hide_viewport=False; o.hide_set(False)
        for collection in o.users_collection: collection.hide_render=False; collection.hide_viewport=False
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=24
scene.cycles.use_denoising=True
scene.render.resolution_x=512; scene.render.resolution_y=1024; scene.render.resolution_percentage=100
scene.render.film_transparent=True
scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='Standard'
world=bpy.data.worlds.new('Neutral Bake World'); scene.world=world; world.use_nodes=True
world.node_tree.nodes.clear()
background=world.node_tree.nodes.new('ShaderNodeBackground'); output=world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs[0],output.inputs['Surface'])
background.inputs[0].default_value=(.75,.75,.75,1)
background.inputs[1].default_value=.8
data=bpy.data.cameras.new('Impostor Camera'); camera=bpy.data.objects.new('Impostor Camera',data)
scene.collection.objects.link(camera); scene.camera=camera; data.type='ORTHO'; data.lens=50
for variant in 'abc':
    obj=bpy.data.objects.get(f'pine_tree_01_{variant}_LOD2'); obj.hide_render=False
    points=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3))); hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    center=(lo+hi)*.5; data.ortho_scale=(hi.z-lo.z)*1.04
    for angle in (0,90):
        a=math.radians(angle); camera.location=center+Vector((math.cos(a)*40,math.sin(a)*40,0))
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(folder/f'impostor_{variant}_{angle}.png')
        bpy.ops.render.render(write_still=True)
    obj.hide_render=True
