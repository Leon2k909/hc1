"""Matched offline daylight inspection renders, not engine screenshots."""
from pathlib import Path
import sys
import math
import bpy
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'Tools'))
import railhead_render as R

OUT = ROOT/'output/cerroblanco/lawn-relief-v1'
R.SCENE = ROOT/'Assets/scenes/maps/CerroBlanco/cerroblanco.scene'
R.STAGE = OUT/'stage'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
placed = {}
for path, world, tint in R.read_scene()['models']:
    path = path.get('Path','') if isinstance(path,dict) else path
    if not R.local_obj_model(path) or 'backdrop' in path or 'vista' in path:
        continue
    if path in placed:
        objects = [o.copy() for o in placed[path]]
        for o in objects:
            scene.collection.objects.link(o)
    else:
        objects = placed[path] = R.map_model(path)
    for o in objects:
        o.matrix_world = world @ R.OBJ_TO_MODEL
candidate = R.map_model('models/maps/cerroblanco/lawn-relief-v1/garden_lawn_relief.vmdl')
for o in candidate:
    o.matrix_world = R.OBJ_TO_MODEL
world = bpy.data.worlds.new('Daylight inspection')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (0.35,0.46,0.65,1)
world.node_tree.nodes['Background'].inputs[1].default_value = 0.65
scene.world = world
light = bpy.data.lights.new('Sun','SUN')
light.energy = 2.0
light.angle = math.radians(1)
sun = bpy.data.objects.new('Sun',light)
scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(56),math.radians(-5),math.radians(-63))
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 3
scene.cycles.texture_limit_render = '1024'
scene.render.use_simplify = True
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.render.resolution_x, scene.render.resolution_y = 1200,800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
views = [('eye',(-1390,-1006,64),(-1660,-1280,4),75),
         ('detail',(-1390,-1006,24),(-1510,-1126,3),65)]
for name, eye, target, fov in views:
    R.set_camera(eye,target,fov)
    for state in ('before','after'):
        for o in candidate:
            o.hide_render = state=='before'
        scene.render.filepath = str(OUT/f'{name}-{state}.png')
        bpy.ops.render.render(write_still=True)
        print('SAVED',scene.render.filepath,flush=True)
print('Matched renders complete',flush=True)
