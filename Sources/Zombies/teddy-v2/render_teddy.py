"""Matched Cycles renders of the old teddy and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_teddy.py -- <project root> <work dir> <out dir> <width> <samples> <views> [lod]

The old teddy is the real geometry and materials cut from Riverside's merged model (old_teddy.py). A face's back is transparent,
because the engine culls backfaces and Cycles doesn't.
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
LOD = int(argv[6]) if len(argv) > 6 else 0
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
scene.cycles.transparent_max_bounces = 16
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "ACES 1.3"
scene.view_settings.exposure = -0.2


def linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def vmat_keys(rel):
    keys = {}
    for line in open(os.path.join(ASSETS, rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def vector(text):
    return [float(x) for x in text.strip("[]").split()]


def material(rel):
    """Maps where the vmat names them and they exist; otherwise its values. Tints are sRGB, as the map's script writes them."""
    keys = vmat_keys(rel)
    mat = bpy.data.materials.new(os.path.basename(rel))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(key, colour):
        path = keys.get(key)
        if not path or path.startswith("[") or not os.path.exists(os.path.join(ASSETS, path)):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(ASSETS, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    tint = [linear(x) for x in vector(keys.get("g_vColorTint", "[1 1 1 1]"))[:3]]
    colour = tex("TextureColor", True)
    if colour:
        nt.links.new(colour.outputs[0], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*tint, 1)
    rough = tex("TextureRoughness", False)
    if rough:
        nt.links.new(rough.outputs[0], b.inputs["Roughness"])
    elif keys.get("TextureRoughness", "").startswith("["):
        b.inputs["Roughness"].default_value = vector(keys["TextureRoughness"])[0]
    metal = tex("TextureMetalness", False)
    if metal:
        nt.links.new(metal.outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = float(keys.get("g_flMetalness", "0"))
    normal = tex("TextureNormal", False)
    if normal:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(normal.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    output = nt.nodes["Material Output"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    both = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], both.inputs[0])
    nt.links.new(b.outputs[0], both.inputs[1])
    nt.links.new(clear.outputs[0], both.inputs[2])
    nt.links.new(both.outputs[0], output.inputs["Surface"])
    return mat


def load_obj(path, material_of):
    positions, uvs, normals = [], [], []
    groups = {}
    current = None
    for line in open(path, encoding="utf-8"):
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
            groups.setdefault(current, [])
        elif tag == "f ":
            groups[current].append([tok.split("/") for tok in line.split()[1:]])
    obs = []
    for name, polys in groups.items():
        vs, us, ns, idx = [], [], [], []
        for poly in polys:
            start = len(vs)
            for p, t, n in poly:
                vs.append(positions[int(p) - 1])
                us.append(uvs[int(t) - 1])
                ns.append(normals[int(n) - 1])
            idx.append(tuple(range(start, start + len(poly))))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vs, [], idx)
        mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set_from_vertices(ns)
        mesh.materials.append(material(material_of(name)))
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


old = load_obj(os.path.join(WORK, "old_teddy.obj"), lambda name: f"materials/riverside/{name}.vmat")
new = load_obj(os.path.join(ASSETS, f"models/zombies/teddy_v2/teddy_lod{LOD}.obj"), lambda name: "materials/zombies/teddy_v2/teddy.vmat")

mesh = bpy.data.meshes.new("ground")
mesh.from_pydata([(-800, -800, 0), (800, -800, 0), (800, 800, 0), (-800, 800, 0)], [], [(0, 1, 2, 3)])
ground_mat = bpy.data.materials.new("ground")
ground_mat.use_nodes = True
ground_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.08, 0.065, 1)
ground_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
mesh.materials.append(ground_mat)
scene.collection.objects.link(bpy.data.objects.new("ground", mesh))

day = bpy.data.worlds.new("day")
day.use_nodes = True
nt = day.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(40))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], nt.nodes["Background"].inputs[0])
nt.nodes["Background"].inputs[1].default_value = 0.7
night = bpy.data.worlds.new("night")
night.use_nodes = True
night.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.055, 1)
night.node_tree.nodes["Background"].inputs[1].default_value = 2.2

sun = bpy.data.lights.new("sun", "SUN")
sun.angle = math.radians(1.6)
sun_ob = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(sun_ob)
# A burn drum nearby at night, as on the pad.
lamp = bpy.data.lights.new("drum fire", "POINT")
lamp.color = (1.0, 0.5, 0.2)
lamp.shadow_soft_size = 3.0
lamp.energy = 14000
lamp_ob = bpy.data.objects.new("drum fire", lamp)
scene.collection.objects.link(lamp_ob)
lamp_ob.location = (46, 54, 42)

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: eye, target, lens, aspect, night.
VIEWS = {
    "whole": ((46, -26, 24), (2.5, 0, 8.5), 40, 0.9, False),
    "face": ((24, -9, 17), (3, 0, 12), 40, 0.9, False),
    "side": ((6, 46, 18), (2.5, 0, 8.5), 40, 0.9, False),
    "back": ((-34, -22, 22), (1, 0, 9), 40, 0.9, False),
}
for name in WANTED:
    eye, target, lens, aspect, is_night = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    lamp_ob.hide_render = not is_night
    if is_night:
        scene.world = night
        scene.view_settings.exposure = 1.2
        sun.energy, sun.color = 0.55, (0.62, 0.72, 1.0)
        sun_ob.rotation_euler = Vector((0.5, 0.9, 0.42)).to_track_quat("Z", "Y").to_euler()
    else:
        scene.world = day
        scene.view_settings.exposure = -0.2
        sun.energy, sun.color = 2.6, (1.0, 0.95, 0.88)
        sun_ob.rotation_euler = Vector((0.72, 1.0, 1.05)).to_track_quat("Z", "Y").to_euler()
    for side, shown, hidden in (("before", old, new), ("after", new, old)):
        for ob in shown:
            ob.hide_render = False
        for ob in hidden:
            ob.hide_render = True
        tail = f"-lod{LOD}" if LOD else ""
        scene.render.filepath = os.path.join(OUT, f"{name}-{side}{tail}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, side, flush=True)
print("renders done", flush=True)
