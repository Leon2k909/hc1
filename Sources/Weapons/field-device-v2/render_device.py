"""Matched Cycles renders of the old field device and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_device.py -- <project root> <out dir> <width> <samples> <views>

Both sit on the same ground under the same sky, sun and exposure, with the ACES 1.3 view transform. The old OBJ has no
normals, and what the engine makes of that isn't known, so it's given the kinder reading: welded and smoothed by angle.
"""
import math
import os
import re
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, OUT = argv[0], argv[1]
WIDTH, SAMPLES = int(argv[2]), int(argv[3])
WANTED = argv[4].split(",")
os.makedirs(OUT, exist_ok=True)
OLD = os.path.join(ROOT, "Assets", "Weapons", "C4", "field_device")
NEW = os.path.join(ROOT, "Assets", "Weapons", "C4", "field_device_v2")

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


def old_material():
    # What the old vmat asks for: its colour map, flat normals, roughness 0.75 and metalness 0.15.
    mat = bpy.data.materials.new("field_device")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    nt.links.new(tex(nt, os.path.join(OLD, "field_device_color.png"), True).outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.75
    b.inputs["Metallic"].default_value = 0.15
    return mat


def new_material():
    keys = {}
    for line in open(os.path.join(NEW, "fd_device.vmat"), encoding="utf-8"):
        m = re.match(r'\s*(\w+)\s+"([^"]+)"\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    path = lambda key: os.path.join(ROOT, "Assets", keys[key])
    mat = bpy.data.materials.new("fd_device")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    colour = tex(nt, path("TextureColor"), True)
    nt.links.new(colour.outputs[0], b.inputs["Base Color"])
    nt.links.new(tex(nt, path("TextureRoughness"), False).outputs[0], b.inputs["Roughness"])
    nt.links.new(tex(nt, path("TextureMetalness"), False).outputs[0], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(nt, path("TextureNormal"), False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    # Self-illumination, as the vmat's brightness and albedo factor describe it.
    nt.links.new(colour.outputs[0], b.inputs["Emission Color"])
    glow = nt.nodes.new("ShaderNodeMath")
    glow.operation = "MULTIPLY"
    glow.inputs[1].default_value = float(keys["g_flSelfIllumBrightness"])
    nt.links.new(tex(nt, path("TextureSelfIllumMask"), False).outputs[0], glow.inputs[0])
    nt.links.new(glow.outputs[0], b.inputs["Emission Strength"])
    return mat


def load_obj(path, make):
    positions, uvs, normals = [], [], []
    faces = []
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
            faces.append([tok.split("/") for tok in line.split()[1:]])
    vs, us, ns, idx = [], [], [], []
    for poly in faces:
        start = len(vs)
        for tok in poly:
            vs.append(positions[int(tok[0]) - 1])
            us.append(uvs[int(tok[1]) - 1])
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
    else:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
        bm.to_mesh(mesh)
        bm.free()
        mesh.set_sharp_from_angle(angle=math.radians(40))
    mesh.materials.append(make())
    ob = bpy.data.objects.new(mesh.name, mesh)
    scene.collection.objects.link(ob)
    return ob


old = load_obj(os.path.join(OLD, "field_device.obj"), old_material)
new = load_obj(os.path.join(NEW, "field_device_lod0.obj"), new_material)

bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, 0))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
nt = gm.node_tree
g = nt.nodes["Principled BSDF"]
wave = nt.nodes.new("ShaderNodeTexNoise")
wave.inputs["Scale"].default_value = 0.4
wave.inputs["Detail"].default_value = 10
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.3
ramp.color_ramp.elements[0].color = (0.1, 0.1, 0.095, 1)
ramp.color_ramp.elements[1].position = 0.7
ramp.color_ramp.elements[1].color = (0.2, 0.19, 0.175, 1)
nt.links.new(wave.outputs[0], ramp.inputs[0])
nt.links.new(ramp.outputs[0], g.inputs["Base Color"])
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
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 2.6
sun.angle = math.radians(2.0)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((-0.5, -1.0, 1.25)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 0.5
cam.clip_end = 5000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co

# name: eye, target, lens, aspect
VIEWS = {
    "hero": ((-19.5, -15.5, 15.0), (0, 0, 1.9), 50, 0.8),
    "hands": ((-15.5, -0.5, 16.0), (-0.3, 0, 2.6), 36, 0.8),
    "top": ((-5.0, 0, 37.0), (0, 0, 2.5), 58, 0.86),
    "keys": ((-8.2, -2.4, 11.5), (-0.55, 0, 3.9), 58, 0.8),
    "side": ((-5.0, -27.0, 9.5), (0, 0, 2.0), 62, 0.6),
    "rear": ((18.0, 18.0, 12.5), (0, 0, 2.0), 52, 0.8),
}
for name in [w for w in WANTED if w in VIEWS]:
    eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        shown.hide_render = False
        hidden.hide_render = True
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
if "lods" in WANTED:
    # The lower LODs from the three-quarter view, to catch holes and broken UVs.
    eye, target, lens, aspect = VIEWS["hero"]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    old.hide_render = new.hide_render = True
    for lod in (1, 2, 3):
        ob = load_obj(os.path.join(NEW, f"field_device_lod{lod}.obj"), new_material)
        scene.render.filepath = os.path.join(OUT, f"lod{lod}.png")
        bpy.ops.render.render(write_still=True)
        ob.hide_render = True
        print("rendered lod", lod, flush=True)
print("renders done", flush=True)
