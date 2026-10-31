"""Matched Cycles renders of the dev-cube drops and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_powerups.py -- <project root> <out dir> <width> <samples> <views> [old|new|both]

Each sits where `ZombiesPowerUp.Spawn` puts it, 36 inches over the ground. The old cube is `box.vmdl` at 0.3 scale, 15 inches on a
side, in the code's tint. The engine's dev box can't be read offline, so it's a flat colour. The game's coloured light is left out.
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
WHICH = argv[5] if len(argv) > 5 else "both"
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


def vmat_keys(rel):
    keys = {}
    for line in open(os.path.join(ASSETS, rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def material(rel):
    keys = vmat_keys(rel)
    mat = bpy.data.materials.new(os.path.basename(rel))
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


def load_obj(path, remap):
    positions, uvs, normals, polys = [], [], [], []
    for line in open(path, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split())
            positions.append((c, a, b))
        elif tag == "vt":
            uvs.append(tuple(map(float, line[3:].split()[:2])))
        elif tag == "vn":
            a, b, c = map(float, line[3:].split())
            normals.append((c, a, b))
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
    mesh.materials.append(material(remap))
    ob = bpy.data.objects.new(os.path.basename(path), mesh)
    scene.collection.objects.link(ob)
    return ob


def cube(name, tint):
    bpy.ops.mesh.primitive_cube_add(size=15, location=(0, 0, 0))
    ob = bpy.context.object
    ob.name = name
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Roughness"].default_value = 0.6
    ob.data.materials.append(mat)
    return ob


# The code's colours: One-Hit Kills is `GetColor`'s red, Clean Sweep falls to its default orange.
SETS = {"one_hit": ("powerup_one_hit", "pu_one_hit", (1.0, 0.25, 0.2)), "clean_sweep": ("powerup_clean_sweep", "pu_clean_sweep", (1.0, 0.5, 0.1))}
objects = {}
for key, (name, mat, tint) in SETS.items():
    if WHICH in ("old", "both"):
        objects[key, "before"] = cube(name, tint)
    if WHICH in ("new", "both"):
        objects[key, "after"] = load_obj(os.path.join(ASSETS, "models/zombies/powerups_v2", name + "_lod0.obj"), f"materials/zombies/powerups_v2/{mat}.vmat")

bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -36))
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

# name: variant, eye, target, lens, aspect. Eye height is a standing player's, 28 above the drop.
VIEWS = {
    "oh_hero": ("one_hit", (26, -34, 20), (0, 0, 0), 50, 0.9),
    "oh_close": ("one_hit", (-9, -22, 11), (0, 0, 2.5), 50, 0.9),
    "oh_far": ("one_hit", (260, -150, 28), (0, 0, 0), 150, 0.75),
    "cs_hero": ("clean_sweep", (24, -36, 20), (0, 0, 0), 50, 0.9),
    "cs_back": ("clean_sweep", (30, 30, 16), (0, 0, 0), 50, 0.9),
    "cs_far": ("clean_sweep", (260, -150, 28), (0, 0, 0), 150, 0.75),
}
for name in WANTED:
    variant, eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = 400 if name.endswith("far") else WIDTH
    scene.render.resolution_y = int(scene.render.resolution_x * aspect)
    for state in ("before", "after"):
        if (variant, state) not in objects:
            continue
        for key, ob in objects.items():
            ob.hide_render = key != (variant, state)
        scene.render.filepath = os.path.join(OUT, f"{name}-{state}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, state, flush=True)
print("renders done", flush=True)
