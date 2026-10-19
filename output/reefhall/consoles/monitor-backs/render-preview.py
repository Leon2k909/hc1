"""Offline Cycles inspection of the actual exported mesh, using its VMAT values."""
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'Tools'))
import railhead_render as V

original_image = V.image
def staged_image(path,data=False):
    if path and not V.is_vector(path):
        staged = OUT/'staging/materials'/Path(path).name
        if staged.is_file():
            path = str(staged)
    return original_image(path,data)
V.image = staged_image

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.threads_mode = 'FIXED'
scene.render.threads = 8
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

text = (OUT/'studio/monitor_pair.vmdl').read_text()
remaps = dict(re.findall(r'\{ from = "([^"]+)" to = "([^"]+)" \}',text))
bpy.ops.wm.obj_import(filepath=str(OUT/'studio/monitor_pair.obj'),forward_axis='Y',up_axis='Z')
for obj in bpy.context.selected_objects:
    obj.matrix_world = V.OBJ_TO_MODEL
    for slot in obj.material_slots:
        name = re.sub(r'\.\d{3}$','',slot.material.name)
        vmat = remaps[name+'.vmat']
        path = OUT/'staging/materials'/Path(vmat).name
        if path.is_file():
            contents = path.read_text()
            keys = dict(re.findall(r'^\s*(\w+)\s+"([^"]*)"',contents,re.M))
            slot.material = V.standard_material(vmat,keys)
        else:
            slot.material = V.material(vmat)

def area(name,position,target,energy,size,color):
    data = bpy.data.lights.new(name,'AREA')
    data.energy = energy
    data.shape = 'DISK'
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name,data)
    scene.collection.objects.link(light)
    light.location = V.plan_to_world(position)
    light.rotation_euler = (V.plan_to_world(target)-light.location).to_track_quat('-Z','Y').to_euler()

world = bpy.data.worlds.new('Neutral studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.38,0.44,0.52,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.45
scene.world = world
area('Broad top',(-20,30,115),(0,10,45),38000,75,(1.0,0.91,0.81))
area('Cool edge',(65,-10,85),(0,10,50),19000,55,(0.58,0.79,1.0))
area('Rear fill',(-65,55,70),(0,10,50),20000,65,(0.82,0.9,1.0))
bpy.ops.mesh.primitive_cube_add(size=1,location=V.plan_to_world((0,10,35.8)))
desk = bpy.context.object
desk.scale = (80,135,1)
desk.data.materials.append(V.standard_material('Preview tabletop',{
    'TextureColor':'[0.48 0.51 0.52 1]','TextureRoughness':'[0.5 0.5 0.5 1]'}))

views = [('monitor-pair',(35,100,78),(0,11,50),56),
         ('charcoal-detail',(-23,68,62),(-23,12,52),51),
         ('aluminium-detail',(33,66,62),(23,12,52),51),
         ('front-check',(0,-108,73),(0,10,51),56)]
for name,eye,target,fov in views:
    V.set_camera(eye,target,fov)
    scene.render.filepath = str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
print('Rendered actual exported geometry to',OUT)
