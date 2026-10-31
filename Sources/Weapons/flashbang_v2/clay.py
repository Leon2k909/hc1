"""A quick grey look at the build, before baking: blender -b ... --python clay.py -- <work dir> <out dir> <views>"""
import math, os, sys
import bpy
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, OUT = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "flash_build.blend"))
scene = bpy.context.scene
scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 24; scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"; scene.render.threads = 4
scene.view_settings.view_transform = "Standard"
for ob in scene.objects:
    ob.hide_render = ob.name != "all_lod0"
ob = bpy.data.objects["all_lod0"]
mat = bpy.data.materials.new("clay"); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]; bsdf.inputs["Base Color"].default_value = (0.42, 0.42, 0.4, 1); bsdf.inputs["Roughness"].default_value = 0.5
ob.data.materials.clear(); ob.data.materials.append(mat)
ob.data.set_sharp_from_angle(angle=math.radians(62))
mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); mod.mode = "FACE_AREA"; mod.weight = 100; mod.keep_sharp = True; mod.thresh = 0.01
world = bpy.data.worlds.new("w"); world.use_nodes = True; world.node_tree.nodes["Background"].inputs[1].default_value = 0.35; scene.world = world
sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.0; so = bpy.data.objects.new("s", sun); scene.collection.objects.link(so)
so.rotation_euler = Vector((0.75, -0.95, 0.85)).to_track_quat("Z", "Y").to_euler()
cam = bpy.data.cameras.new("c"); cam.clip_start = 0.05; co = bpy.data.objects.new("c", cam); scene.collection.objects.link(co); scene.camera = co
VIEWS = {"front": ((11.5, -10.0, 5.2), (0, 0, 2.7), 70), "lever": ((-11.5, -8.8, 5.8), (-0.1, 0, 2.7), 70), "ports": ((6.8, -5.8, 3.0), (0, 0, 2.2), 70), "top": ((-2.8, -3.2, 8.6), (-0.1, 0.05, 4.7), 85), "pin": ((-3.4, 9.4, 7.0), (-0.2, 0.1, 4.2), 80), "base": ((5.0, -6.0, -3.5), (0, 0, 1.0), 70)}
scene.render.resolution_x = scene.render.resolution_y = 640
os.makedirs(OUT, exist_ok=True)
for name in argv[2].split(","):
    eye, target, lens = VIEWS[name]
    co.location = eye; co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler(); cam.lens = lens
    scene.render.filepath = os.path.join(OUT, f"clay-{name}.png"); bpy.ops.render.render(write_still=True); print("rendered", name, flush=True)
print("renders done", flush=True)
