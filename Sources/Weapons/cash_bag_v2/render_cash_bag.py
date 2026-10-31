"""Matched Cycles renders of the old dev bag and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_cash_bag.py -- <project root> <work dir> <out dir> <width> <samples> <views> [old|new|both]

The old mesh comes from read_old.py, out of its compiled file. Its material in the game is `materials/dev/white_flat`, so it's white here.
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, WORK, OUT = argv[0], argv[1], argv[2]
WIDTH, SAMPLES = int(argv[3]), int(argv[4])
WANTED = argv[5].split(",")
WHICH = argv[6] if len(argv) > 6 else "both"
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")

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
scene.view_settings.exposure = -0.2


def new_material():
    keys = {}
    for line in open(os.path.join(ASSETS, "Weapons/Special/Cash_Bag/cash_bag_v2/cb_bag.vmat"), encoding="utf-8"):
        m = re.match(r'\s*(\w+)\s+"([^"]+)"\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    mat = bpy.data.materials.new("cb_bag")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(path, colour):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(ASSETS, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        n.interpolation = "Cubic"
        return n

    nt.links.new(tex(keys["TextureColor"], True).outputs[0], b.inputs["Base Color"])
    nt.links.new(tex(keys["TextureRoughness"], False).outputs[0], b.inputs["Roughness"])
    nt.links.new(tex(keys["TextureMetalness"], False).outputs[0], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(keys["TextureNormal"], False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def white_flat():
    mat = bpy.data.materials.new("white_flat")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.8, 0.8, 0.8, 1)
    b.inputs["Roughness"].default_value = 0.6
    return mat


def load_obj(path, mat, swap):
    positions, uvs, normals, polys = [], [], [], []
    for line in open(path, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split())
            positions.append((c, a, b) if swap else (a, b, c))
        elif tag == "vt":
            uvs.append(tuple(map(float, line[3:].split()[:2])))
        elif tag == "vn":
            a, b, c = map(float, line[3:].split())
            normals.append((c, a, b) if swap else (a, b, c))
        elif tag == "f ":
            polys.append([tok.split("/") for tok in line.split()[1:]])
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        start = len(vs)
        for tok in poly:
            vs.append(positions[int(tok[0]) - 1])
            us.append(uvs[int(tok[1]) - 1])
            ns.append(normals[int(tok[2]) - 1])
        idx.append(tuple(range(start, start + len(poly))))
    mesh = bpy.data.meshes.new(os.path.basename(path))
    mesh.from_pydata(vs, [], idx)
    layer = mesh.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    mesh.normals_split_custom_set(ns)
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(os.path.basename(path), mesh)
    scene.collection.objects.link(ob)
    return ob


objects = {}
if WHICH in ("old", "both"):
    objects["before"] = load_obj(os.path.join(WORK, "old", "old_mesh_0.obj"), white_flat(), False)
if WHICH in ("new", "both"):
    objects["after"] = load_obj(os.path.join(ASSETS, "Weapons/Special/Cash_Bag/cash_bag_v2/cash_bag_lod0.obj"), new_material(), True)

bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -0.08))
ground = bpy.context.object
gm = bpy.data.materials.new("concrete")
gm.use_nodes = True
g = gm.node_tree.nodes["Principled BSDF"]
g.inputs["Base Color"].default_value = (0.2, 0.195, 0.185, 1)
g.inputs["Roughness"].default_value = 0.88
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
bg.inputs[1].default_value = 0.85
seen = nt.nodes.new("ShaderNodeBackground")
seen.inputs[0].default_value = (0.45, 0.52, 0.62, 1)
path = nt.nodes.new("ShaderNodeLightPath")
choose = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(path.outputs["Is Camera Ray"], choose.inputs[0])
nt.links.new(bg.outputs[0], choose.inputs[1])
nt.links.new(seen.outputs[0], choose.inputs[2])
nt.links.new(choose.outputs[0], nt.nodes["World Output"].inputs[0])
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.4
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = (Vector((1.0, -0.55, 1.1))).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co

# name: eye, target, lens, aspect. "far" is a crop of 1080p at 60 degrees, from 8 metres, of a bag lying where it was dropped.
VIEWS = {
    "hero": ((30, -38, 28), (0, 0, 4), 50, 0.7),
    "top": ((14, -10, 44), (0, 0, 6), 50, 0.72),
    "side": ((56, 8, 18), (0, 0, 5), 50, 0.5),
    "end": ((-24, -40, 16), (0, -6, 5), 50, 0.7),
    "far": ((260, -150, 64), (0, 0, 5), 150, 0.75),
}
for name in WANTED:
    eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = 400 if name == "far" else WIDTH
    scene.render.resolution_y = int(scene.render.resolution_x * aspect)
    for state in ("before", "after"):
        if state not in objects:
            continue
        for key, ob in objects.items():
            ob.hide_render = key != state
        scene.render.filepath = os.path.join(OUT, f"{name}-{state}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, state, flush=True)
print("renders done", flush=True)
