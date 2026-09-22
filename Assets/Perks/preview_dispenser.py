"""Render a quick design preview: blender -b perk_dispenser.blend -P preview_dispenser.py"""
import bpy
from mathutils import Vector
from pathlib import Path

folder = Path(__file__).resolve().parent
colors = {'dark':(.035,.045,.04,1),'metal':(.36,.35,.27,1),
          'enamel':(.23,.35,.29,1),'accent':(.12,.85,.38,1)}
for group, rgba in colors.items():
    obj = bpy.data.objects.get('perk_'+group)
    if not obj: continue
    mat = bpy.data.materials.new(group)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgba
    bsdf.inputs['Metallic'].default_value = .55 if group == 'metal' else .1
    bsdf.inputs['Roughness'].default_value = .3 if group == 'metal' else .48
    if group == 'enamel':
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(folder/'aged_enamel_seafoam.png'))
        mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    obj.data.materials.clear()
    obj.data.materials.append(mat)

# Image plane has an exact 1:1 UV rectangle facing +X.
mesh = bpy.data.meshes.new('card')
mesh.from_pydata([(29.29,-14.8,36.7),(29.29,14.8,36.7),
                  (29.29,14.8,79.3),(29.29,-14.8,79.3)],[],[(0,1,2,3)])
mesh.update()
uv = mesh.uv_layers.new()
for poly in mesh.polygons:
    for loop_id, coord in zip(poly.loop_indices,[(0,0),(1,0),(1,1),(0,1)]):
        uv.data[loop_id].uv=coord
card = bpy.data.objects.new('Speed Cola artwork',mesh)
bpy.context.collection.objects.link(card)
mat = bpy.data.materials.new('printed artwork')
mat.use_nodes=True
nodes=mat.node_tree.nodes
tex=nodes.new('ShaderNodeTexImage')
tex.image=bpy.data.images.load(str(folder/'speedcola_label.png'))
mat.node_tree.links.new(tex.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
card.data.materials.append(mat)

def aim(obj, point): obj.rotation_euler=(Vector(point)-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(135,-150,105))
camera=bpy.context.object
aim(camera,(0,0,48))
camera.data.type='ORTHO'
camera.data.ortho_scale=125
bpy.context.scene.camera=camera
for loc,power,size in [((45,-65,150),2200,90),((-65,40,110),1400,80)]:
    bpy.ops.object.light_add(type='AREA',location=loc)
    light=bpy.context.object
    light.data.energy=power
    light.data.shape='DISK'
    light.data.size=size
    aim(light,(0,0,45))
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.view_settings.view_transform='Standard'
scene.view_settings.look='Medium High Contrast'
scene.view_settings.exposure=1.2
scene.render.resolution_x=800
scene.render.resolution_y=900
scene.render.resolution_percentage=100
scene.render.filepath=str(folder/'perk_dispenser_preview.png')
bpy.ops.render.render(write_still=True)
