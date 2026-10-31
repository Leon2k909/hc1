"""Matched Cycles renders of the old HC1 rifle suppressor and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_suppressor.py -- <project root> <out dir> <width> <samples> <views> [old]

Both float over the same ground under the same sky, sun and exposure, with the ACES 1.3 view transform. Pass old to render
only the old model, before the new one exists. The old OBJ's maps are its shared colour atlas with the flat roughness and
metalness its two vmats give, since the default roughness texture it multiplies isn't known here.
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, OUT = argv[0], argv[1]
WIDTH, SAMPLES = int(argv[2]), int(argv[3])
WANTED = argv[4].split(",")
OLD_ONLY = len(argv) > 5 and argv[5] == "old"
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
OLD = os.path.join(ASSETS, "attachments", "hc1", "rifle_suppressor")
NEW = os.path.join(ASSETS, "attachments", "hc1", "rifle_suppressor_v2")

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
scene.view_settings.exposure = 0.2


def tex(nt, path, colour):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(path, check_existing=True)
    n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    n.interpolation = "Cubic"
    return n


def old_material(name):
    keys = {}
    for line in open(os.path.join(ASSETS, "attachments", "hc1", "materials", name + ".vmat"), encoding="utf-8"):
        m = re.match(r'\s*"?(\w+)"?\s+"([^"]+)"\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex(nt, os.path.join(ASSETS, keys["TextureColor"]), True).outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = float(keys["g_flRoughnessScaleFactor"])
    b.inputs["Metallic"].default_value = float(keys["g_flMetalness"])
    return mat


def new_material(name):
    keys = {}
    for line in open(os.path.join(NEW, "rs_can.vmat"), encoding="utf-8"):
        m = re.match(r'\s*(\w+)\s+"([^"]+)"\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    path = lambda key: os.path.join(ASSETS, keys[key])
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex(nt, path("TextureColor"), True).outputs[0], b.inputs["Base Color"])
    nt.links.new(tex(nt, path("TextureRoughness"), False).outputs[0], b.inputs["Roughness"])
    nt.links.new(tex(nt, path("TextureMetalness"), False).outputs[0], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(nt, path("TextureNormal"), False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def load_obj(path, make):
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
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
        elif line.startswith("usemtl"):
            current = line.split()[1]
            faces.setdefault(current, [])
        elif tag == "f ":
            faces[current].append([tok.split("/") for tok in line.split()[1:]])
    obs = []
    for name, polys in faces.items():
        vs, us, ns, idx = [], [], [], []
        for poly in polys:
            start = len(vs)
            for tok in poly:
                vs.append(positions[int(tok[0]) - 1])
                us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
                if len(tok) > 2 and tok[2]:
                    ns.append(normals[int(tok[2]) - 1])
            idx.append(tuple(range(start, start + len(poly))))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vs, [], idx)
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        if len(ns) == len(vs):
            mesh.normals_split_custom_set(ns)
        mesh.materials.append(make(name))
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


old = load_obj(os.path.join(OLD, "rifle_suppressor.obj"), old_material)
new = [] if OLD_ONLY else load_obj(os.path.join(NEW, "rifle_suppressor_lod0.obj"), new_material)

bpy.ops.mesh.primitive_plane_add(size=800, location=(0, 0, -1.6))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
g = gm.node_tree.nodes["Principled BSDF"]
g.inputs["Base Color"].default_value = (0.11, 0.11, 0.105, 1)
g.inputs["Roughness"].default_value = 0.86
ground.data.materials.append(gm)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(310))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.9
# The camera sees a plain backdrop, so the low views don't have a building behind them. The light is unchanged.
seen = nt.nodes.new("ShaderNodeBackground")
seen.inputs[0].default_value = (0.19, 0.2, 0.22, 1)
path = nt.nodes.new("ShaderNodeLightPath")
choose = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(path.outputs["Is Camera Ray"], choose.inputs[0])
nt.links.new(bg.outputs[0], choose.inputs[1])
nt.links.new(seen.outputs[0], choose.inputs[2])
nt.links.new(choose.outputs[0], nt.nodes["World Output"].inputs[0])
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 2.6
sun.angle = math.radians(2.0)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((-0.5, -1.0, 1.25)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 0.1
cam.clip_end = 2000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co

# name: eye, target, lens, aspect. The old model's forward is +X.
VIEWS = {
    "hero": ((-3.6, -8.2, 4.4), (3.2, 0, 0), 58, 0.62),
    "eye": ((-5.2, -1.9, 3.3), (3.6, 0, -0.2), 44, 0.62),
    "side": ((3.18, -15.0, 0.8), (3.18, 0, 0), 58, 0.5),
    "muzzle": ((10.0, -3.2, 2.5), (5.6, 0, 0), 56, 0.8),
    "mount": ((-3.8, 2.8, 2.5), (0.7, 0, 0), 56, 0.8),
}
for name in [w for w in WANTED if w in VIEWS]:
    eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        if not shown:
            continue
        for ob in shown:
            ob.hide_render = False
        for ob in hidden:
            ob.hide_render = True
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
if "lods" in WANTED:
    eye, target, lens, aspect = VIEWS["hero"]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for ob in old + new:
        ob.hide_render = True
    for lod in (1, 2, 3):
        obs = load_obj(os.path.join(NEW, f"rifle_suppressor_lod{lod}.obj"), new_material)
        scene.render.filepath = os.path.join(OUT, f"lod{lod}.png")
        bpy.ops.render.render(write_still=True)
        for ob in obs:
            ob.hide_render = True
        print("rendered lod", lod, flush=True)
print("renders done", flush=True)
