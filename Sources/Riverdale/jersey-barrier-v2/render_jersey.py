"""Matched Cycles renders of the old jersey barrier, from the map's own code, and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python-exit-code 1 --python render_jersey.py -- <project root> <work dir> <out dir> <width> <samples> <views> [old]

Both stand on the same wet concrete under the same overcast sky and exposure, as these two rain-soaked maps are lit, with the ACES 1.3
view transform. Pass old to render only the old model. Its material is the map's rv_precast, which tiles every 64 inches.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, WORK, OUT = argv[0], argv[1], argv[2]
WIDTH, SAMPLES = int(argv[3]), int(argv[4])
WANTED = argv[5].split(",")
OLD_ONLY = len(argv) > 6 and argv[6] == "old"
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models", "props", "riverdale", "jersey_barrier_v2")
PRECAST = os.path.join(ASSETS, "materials", "riverdale")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 5
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "ACES 1.3"
scene.view_settings.exposure = 0.3


def tex(nt, path, colour):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return n


def material(name, color, rough, normal, metal=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex(nt, color, True).outputs[0], b.inputs["Base Color"])
    nt.links.new(tex(nt, rough, False).outputs[0], b.inputs["Roughness"])
    if metal:
        nt.links.new(tex(nt, metal, False).outputs[0], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(nt, normal, False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def load_obj(path, mat):
    positions, uvs, normals = [], [], []
    polys = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split()[:3])
            positions.append((c, a, b))
        elif tag == "vt":
            uvs.append(tuple(map(float, line[3:].split()[:2])))
        elif tag == "vn":
            a, b, c = map(float, line[3:].split()[:3])
            normals.append((c, a, b))
        elif tag == "f ":
            polys.append([tok.split("/") for tok in line.split()[1:]])
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        start = len(vs)
        for tok in poly:
            vs.append(positions[int(tok[0]) - 1])
            us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
            if len(tok) > 2 and tok[2]:
                ns.append(normals[int(tok[2]) - 1])
        idx.append(tuple(range(start, start + len(poly))))
    mesh = bpy.data.meshes.new(os.path.basename(path))
    mesh.from_pydata(vs, [], idx)
    layer = mesh.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    if len(ns) == len(vs):
        mesh.normals_split_custom_set(ns)
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(mesh.name, mesh)
    scene.collection.objects.link(ob)
    return ob


old_mat = material("rv_precast", os.path.join(PRECAST, "rv_precast_color.jpg"), os.path.join(PRECAST, "rv_precast_rough.png"), os.path.join(PRECAST, "rv_precast_normal.png"))
old = load_obj(os.path.join(WORK, "old", "old_barrier.obj"), old_mat)
new = None
if not OLD_ONLY:
    new_mat = material("jb_concrete", os.path.join(NEW, "jb_concrete_color.png"), os.path.join(NEW, "jb_concrete_rough.png"), os.path.join(NEW, "jb_concrete_normal.png"), os.path.join(NEW, "jb_concrete_metal.png"))
    new = load_obj(os.path.join(NEW, "jersey_barrier_lod0.obj"), new_mat)

# Wet asphalt, plain so it doesn't compete, and the same for both.
bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, 0))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
nt = gm.node_tree
g = nt.nodes["Principled BSDF"]
wave = nt.nodes.new("ShaderNodeTexNoise")
wave.inputs["Scale"].default_value = 0.09
wave.inputs["Detail"].default_value = 8
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.35
ramp.color_ramp.elements[0].color = (0.035, 0.035, 0.036, 1)
ramp.color_ramp.elements[1].position = 0.7
ramp.color_ramp.elements[1].color = (0.075, 0.074, 0.072, 1)
nt.links.new(wave.outputs[0], ramp.inputs[0])
nt.links.new(ramp.outputs[0], g.inputs["Base Color"])
g.inputs["Roughness"].default_value = 0.52
ground.data.materials.append(gm)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(130))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.8
seen = nt.nodes.new("ShaderNodeBackground")
seen.inputs[0].default_value = (0.26, 0.28, 0.3, 1)
path = nt.nodes.new("ShaderNodeLightPath")
choose = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(path.outputs["Is Camera Ray"], choose.inputs[0])
nt.links.new(bg.outputs[0], choose.inputs[1])
nt.links.new(seen.outputs[0], choose.inputs[2])
nt.links.new(choose.outputs[0], nt.nodes["World Output"].inputs[0])
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 1.5
sun.angle = math.radians(9.0)
sun.color = (0.96, 0.97, 1.0)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((-0.55, -0.75, 1.0)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co

# name: eye, target, lens, aspect. Player's eyes are about 64 in up: "cover" is what you see crouched up against one.
VIEWS = {
    "hero": ((-130, -165, 92), (0, 0, 14), 42, 0.62),
    "player": ((-46, -120, 64), (0, 0, 15), 36, 0.62),
    "cover": ((-24, -34, 40), (2, -5, 20), 30, 0.62),
    "broken": ((95, -52, 58), (54, 0, 22), 40, 0.75),
    "end": ((-108, 38, 40), (-58, 0, 16), 36, 0.75),
}
for name in [w for w in WANTED if w in VIEWS]:
    eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        if shown is None:
            continue
        shown.hide_render = False
        if hidden is not None:
            hidden.hide_render = True
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
if "lods" in WANTED and new is not None:
    eye, target, lens, aspect = VIEWS["hero"]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    old.hide_render = new.hide_render = True
    for lod in (1, 2, 3):
        ob = load_obj(os.path.join(NEW, f"jersey_barrier_lod{lod}.obj"), new_mat)
        scene.render.filepath = os.path.join(OUT, f"lod{lod}.png")
        bpy.ops.render.render(write_still=True)
        ob.hide_render = True
        print("rendered lod", lod, flush=True)
print("renders done", flush=True)
