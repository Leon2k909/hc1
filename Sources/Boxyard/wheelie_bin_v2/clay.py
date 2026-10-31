"""A quick grey look at the build, before baking: blender -b ... --python clay.py -- <work dir> <out dir> <views>"""
import math, os, sys
import bpy
from mathutils import Vector
argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, OUT = argv[0], argv[1]
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "wheelie_bin_build.blend"))
scene = bpy.context.scene
scene.render.engine = "CYCLES"; scene.cycles.device = "CPU"; scene.cycles.samples = 24; scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"; scene.render.threads = 4
scene.view_settings.view_transform = "Standard"
for ob in scene.objects:
    ob.hide_render = ob.name != "wheelie_bin_lod0"
ob = bpy.data.objects["wheelie_bin_lod0"]
mat = bpy.data.materials.new("clay"); mat.use_nodes = True
bsdf = mat.node_tree.nodes["Principled BSDF"]; bsdf.inputs["Base Color"].default_value = (0.42, 0.42, 0.4, 1); bsdf.inputs["Roughness"].default_value = 0.5
ob.data.materials.clear(); ob.data.materials.append(mat)
ob.data.set_sharp_from_angle(angle=math.radians(62))
mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); mod.mode = "FACE_AREA"; mod.weight = 100; mod.keep_sharp = True; mod.thresh = 0.01
world = bpy.data.worlds.new("w"); world.use_nodes = True; world.node_tree.nodes["Background"].inputs[1].default_value = 0.35; scene.world = world
sun = bpy.data.lights.new("s", "SUN"); sun.energy = 3.0; so = bpy.data.objects.new("s", sun); scene.collection.objects.link(so)
so.rotation_euler = Vector((0.75, -0.95, 0.85)).to_track_quat("Z", "Y").to_euler()
cam = bpy.data.cameras.new("c"); cam.clip_start = 0.5; co = bpy.data.objects.new("c", cam); scene.collection.objects.link(co); scene.camera = co
VIEWS = {"front": ((46, 62, 34), (0, 0, 21), 45), "back": ((-40, -66, 36), (0, -2, 20), 45), "side": ((72, -10, 30), (0, 0, 21), 45), "top": ((30, 34, 78), (0, 0, 36), 45), "wheel": ((26, -30, 12), (8, -12, 6), 45)}
scene.render.resolution_x = scene.render.resolution_y = 640
os.makedirs(OUT, exist_ok=True)
for name in argv[2].split(","):
    eye, target, lens = VIEWS[name]
    co.location = eye; co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler(); cam.lens = lens
    scene.render.filepath = os.path.join(OUT, f"clay-{name}.png"); bpy.ops.render.render(write_still=True); print("rendered", name, flush=True)
print("renders done", flush=True)
