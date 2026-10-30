"""Quick look at a flag grid: blender -b --factory-startup -t 2 --python preview_flag.py -- <work dir> <out png>"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
data = np.load(os.path.join(argv[0], "flag_shape.npz"))
grid = data["grid"]
rows, cols = grid.shape[:2]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
faces = []
for j in range(rows - 1):
    for i in range(cols - 1):
        a = j * cols + i
        faces.append((a, a + 1, a + cols + 1, a + cols))
mesh = bpy.data.meshes.new("flag")
mesh.from_pydata(grid.reshape(-1, 3).tolist(), [], faces)
for poly in mesh.polygons:
    poly.use_smooth = True
ob = bpy.data.objects.new("flag", mesh)
scene.collection.objects.link(ob)
m = bpy.data.materials.new("cloth")
m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.62, 0.05, 0.05, 1)
m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
mesh.materials.append(m)

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 12
scene.cycles.use_denoising = False
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.render.resolution_x, scene.render.resolution_y = 720, 460
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.5
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(-35))
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
scene.world = w
cam = bpy.data.cameras.new("c")
cam.lens = 60
cam.clip_end = 5000
co = bpy.data.objects.new("c", cam)
scene.collection.objects.link(co)
scene.camera = co
target = Vector((19, 0, 11))
co.location = target + Vector((14, -92, 4))
co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = argv[1]
bpy.ops.render.render(write_still=True)
