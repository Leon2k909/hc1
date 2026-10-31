"""Matched Cycles renders of a shipped town house door and v2's exported files, in the same plain wall. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_door.py -- <project root> <out dir> <width> <samples> <outer|inner> <views>
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
VARIANT = argv[4]
WANTED = argv[5].split(",")
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
LEAF = {"outer": (-0.875, 44.75, -41.625, 43.75), "inner": (-0.6875, 38.9375, -41.625, 39.75)}[VARIANT]

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
    """Any of these doors' vmats, old or new: maps where they have them, values where they don't."""
    keys = vmat_keys(rel)
    mat = bpy.data.materials.new(os.path.basename(rel))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(path, colour):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(ASSETS, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    nt.links.new(tex(keys["TextureColor"], True).outputs[0], b.inputs["Base Color"])
    nt.links.new(tex(keys["TextureRoughness"], False).outputs[0], b.inputs["Roughness"])
    if "TextureMetalness" in keys:
        nt.links.new(tex(keys["TextureMetalness"], False).outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = float(keys.get("g_flMetalness", "0"))
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(keys["TextureNormal"], False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def load_obj(path, remaps):
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
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
        elif line.startswith("usemtl"):
            current = line.split()[1]
            faces.setdefault(current, [])
        elif tag == "f ":
            faces[current].append([tok.split("/") for tok in line.split()[1:]])
    obs = []
    for paint, polys in faces.items():
        vs, us, ns, idx = [], [], [], []
        for poly in polys:
            start = len(vs)
            for tok in poly:
                vs.append(positions[int(tok[0]) - 1])
                us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
                if len(tok) > 2 and tok[2]:
                    ns.append(normals[int(tok[2]) - 1])
            idx.append(tuple(range(start, start + len(poly))))
        mesh = bpy.data.meshes.new(paint)
        mesh.from_pydata(vs, [], idx)
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
        if len(ns) == len(vs):
            mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
            mesh.normals_split_custom_set(ns)
        mesh.materials.append(material(remaps[paint]))
        ob = bpy.data.objects.new(paint, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


def remaps_of(vmdl):
    return dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', open(vmdl, encoding="utf-8").read()))


old_stem = os.path.join(ASSETS, f"models/buildings/town_house/town_house_door_{VARIANT}")
new_dir = os.path.join(ASSETS, "models/buildings/town_house/door_v2")
old = load_obj(old_stem + ".obj", remaps_of(old_stem + ".vmdl"))
new = load_obj(os.path.join(new_dir, f"door_{VARIANT}_lod0.obj"), remaps_of(os.path.join(new_dir, f"door_{VARIANT}.vmdl")))

# The same plain plaster wall, floor and dark room beyond for both.
y0, y1, z0, z1 = LEAF


def block(name, lo, hi, colour, rough=0.85):
    mesh = bpy.data.meshes.new(name)
    x0, a0, b0 = lo
    x1, a1, b1 = hi
    v = [(x0, a0, b0), (x1, a0, b0), (x1, a1, b0), (x0, a1, b0), (x0, a0, b1), (x1, a0, b1), (x1, a1, b1), (x0, a1, b1)]
    mesh.from_pydata(v, [], [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*colour, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = rough
    mesh.materials.append(m)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)


plaster = (0.56, 0.52, 0.45)
frame_c = (0.16, 0.14, 0.11)
block("wall left", (-3, y0 - 90, z0), (3, y0 - 3, z1 + 60), plaster)
block("wall right", (-3, y1 + 3, z0), (3, y1 + 90, z1 + 60), plaster)
block("wall top", (-3, y0 - 3, z1 + 3), (3, y1 + 3, z1 + 60), plaster)
block("frame left", (-3.2, y0 - 3, z0), (3.2, y0 - 0.06, z1 + 3), frame_c, 0.55)
block("frame right", (-3.2, y1 + 0.06, z0), (3.2, y1 + 3, z1 + 3), frame_c, 0.55)
block("frame top", (-3.2, y0 - 3, z1 + 0.06), (3.2, y1 + 3, z1 + 3), frame_c, 0.55)
block("room", (-14, y0 - 90, z0), (-12, y1 + 90, z1 + 60), (0.02, 0.02, 0.02))
block("floor", (-400, -400, z0 - 2), (400, 400, z0 - 0.06), (0.16, 0.15, 0.13), 0.8)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(40))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.8
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.0
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
# Low and raking across the door's face, which is what shows a surface up or lets it down.
so.rotation_euler = Vector((1.0, -0.8, 0.9)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
mid_y = (y0 + y1) / 2
mid_z = (z0 + z1) / 2
# name: eye, target, lens, aspect. The camera's on the door's +X face, as a player outside a front door is.
VIEWS = {
    "whole": ((120, mid_y - 72, 18), (0, mid_y, mid_z + 2), 42, 1.2),
    "lever": ((22, y1 - 22, -1.5), (0.6, y1 - 6, -5), 40, 0.85),
    "panels": ((54, mid_y + 26, 12), (0, mid_y, 14), 40, 0.85),
    "low": ((42, mid_y - 22, -30), (0, mid_y, -30), 40, 0.7),
}
for name in WANTED:
    eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        for ob in shown:
            ob.hide_render = False
        for ob in hidden:
            ob.hide_render = True
        scene.render.filepath = os.path.join(OUT, f"{VARIANT}-{name}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
print("renders done", flush=True)
