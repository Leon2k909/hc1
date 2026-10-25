"""Offline construction review of the staged clock-building casks."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
REV=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'r2'
FOLDER=ROOT/f'output/belltower/barrels-v2/{REV}'
ASSETS=ROOT/'Assets'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=1100;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'

def texture(nodes,path,colour=False):
    n=nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True)
    if not colour:n.image.colorspace_settings.name='Non-Color'
    return n

def material(name):
    m=bpy.data.materials.new(name+'-review');m.use_nodes=True
    nodes,links=m.node_tree.nodes,m.node_tree.links;s=nodes.get('Principled BSDF')
    if name in ('furniture_wood','furniture_wood_dark'):
        prefix=ASSETS/'materials/belltower/scans/brown_planks_03'
        tex=texture(nodes,str(prefix)+'_diffuse_4k.png',True)
        tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
        tint.inputs[2].default_value=(1.08,.97,.82,1) if name=='furniture_wood' else (.83,.73,.60,1)
        links.new(tex.outputs['Color'],tint.inputs[1]);links.new(tint.outputs[0],s.inputs['Base Color'])
        normal=texture(nodes,str(prefix)+'_nor_gl_4k.png');normalmap=nodes.new('ShaderNodeNormalMap')
        links.new(normal.outputs[0],normalmap.inputs['Color']);links.new(normalmap.outputs[0],s.inputs['Normal'])
        links.new(texture(nodes,str(prefix)+'_rough_4k.png').outputs[0],s.inputs['Roughness'])
    elif name=='barrel_rust':
        s.inputs['Base Color'].default_value=(.13,.045,.014,1);s.inputs['Roughness'].default_value=.95
    elif name=='garden_endgrain':
        s.inputs['Base Color'].default_value=(.22,.135,.066,1);s.inputs['Roughness'].default_value=.85
    else:
        s.inputs['Base Color'].default_value=(.025,.029,.027,1);s.inputs['Metallic'].default_value=.65;s.inputs['Roughness'].default_value=.48
    return m

def aim(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.wm.obj_import(filepath=str(FOLDER/'stage/Assets/models/maps/belltower/barrels-v2/west.obj'),forward_axis='NEGATIVE_Z',up_axis='Y')
objects=[o for o in scene.objects if o.type=='MESH']
for o in objects:
    o.scale=(.0254,)*3
    for slot in o.material_slots:slot.material=material(slot.material.name)
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(p) for o in objects for p in o.bound_box]
lo=Vector(tuple(min(p[k] for p in points) for k in range(3)));hi=Vector(tuple(max(p[k] for p in points) for k in range(3)))
centre=(lo+hi)*.5;extent=max(hi-lo)
bpy.ops.mesh.primitive_plane_add(size=200,location=(centre.x,centre.y,lo.z-.005))
floor=bpy.data.materials.new('studio-floor');floor.diffuse_color=(.12,.12,.11,1);bpy.context.object.data.materials.append(floor)
world=bpy.data.worlds.new('review-world');world.use_nodes=True;scene.world=world
world.node_tree.nodes.get('Background').inputs[0].default_value=(.55,.63,.78,1)
world.node_tree.nodes.get('Background').inputs[1].default_value=.45
for offset,power,size in [((-.8,-1.2,1.7),550,.9),((1.2,1,.8),160,1.1)]:
    bpy.ops.object.light_add(type='AREA',location=centre+Vector(offset)*extent)
    lamp=bpy.context.object;lamp.data.energy=power*extent*extent;lamp.data.size=size*extent;aim(lamp,centre)
bpy.ops.object.camera_add(location=centre+Vector((-.65,-1.35,.8))*extent)
camera=bpy.context.object;camera.data.lens=46;aim(camera,centre);scene.camera=camera
scene.render.filepath=str(FOLDER/'construction.png');bpy.ops.render.render(write_still=True)
print('REVIEW '+scene.render.filepath,flush=True)
