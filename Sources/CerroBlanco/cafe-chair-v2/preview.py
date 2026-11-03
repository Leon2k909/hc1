"""Quick look at the chair's bare build: grey by finish, a sun and a sky, a few views. Writes preview_<view>.png into the work folder.

blender -b --factory-startup -t 4 --python preview.py -- <work dir> <project root>
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK = argv[0]
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "chair_build.blend"))
scene = bpy.context.scene
for ob in list(scene.objects):
    if ob.name != "chair_lod0":
        bpy.data.objects.remove(ob)
ob = bpy.data.objects["chair_lod0"]
ob.scale = (0.0254,) * 3

mat = bpy.data.materials.new("finish")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
attr = nt.nodes.new("ShaderNodeVertexColor")
attr.layer_name = "facts"
sep = nt.nodes.new("ShaderNodeSeparateColor")
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "CONSTANT"
colours = [(0.0, (0.42, 0.25, 0.12, 1)), (1 / 16 - 0.01, (0.05, 0.05, 0.055, 1)), (2 / 16 - 0.01, (0.02, 0.02, 0.02, 1)), (3 / 16 - 0.01, (0.01, 0.01, 0.01, 1)), (4 / 16 - 0.01, (0.6, 0.6, 0.6, 1)), (5 / 16 - 0.01, (0.75, 0.72, 0.65, 1)), (6 / 16 - 0.01, (0.03, 0.03, 0.035, 1))]
ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = colours[0]
ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = colours[1]
for pos, col in colours[2:]:
    e = ramp.color_ramp.elements.new(pos)
    e.color = col
nt.links.new(attr.outputs[0], sep.inputs[0])
nt.links.new(sep.outputs[0], ramp.inputs[0])
nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.6
ob.data.materials.clear()
ob.data.materials.append(mat)

bpy.ops.mesh.primitive_plane_add(size=8)
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.38, 0.32, 1)
ground.data.materials.append(gm)
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 4.0
sun_ob = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(sun_ob)
sun_ob.rotation_euler = (math.radians(40), math.radians(10), math.radians(35))
world = bpy.data.worlds.new("sky")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
scene.world = world
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = 960, 640
scene.view_settings.view_transform = "AgX"
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def look(eye, target, lens):
    eye, target = Vector(eye) * 0.0254, Vector(target) * 0.0254
    cam.location = eye
    cam.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens


for name, eye, target, lens in (
    ("front", (46, -30, 34), (0, 0, 16), 40),
    ("back", (-44, 28, 36), (-2, 0, 18), 40),
    ("side", (0, -60, 22), (0, 0, 16), 38),
    ("seat", (16, -12, 30), (0, 0, 18), 35),
    ("foot", (16, -18, 6), (7, -7.6, 2), 45),
    ("top", (-2, -8, 52), (-4, 0, 22), 35),
):
    look(eye, target, lens)
    scene.render.filepath = os.path.join(WORK, f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)
