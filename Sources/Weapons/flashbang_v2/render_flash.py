"""Matched Cycles renders of the old flashbang and v2's exported files: same camera, light and exposure. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_flash.py -- <project root> <work dir> <out dir> <width> <samples> <views> [old,new] [lod]
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
WHICH = argv[6].split(",") if len(argv) > 6 else ["old", "new"]
LOD = int(argv[7]) if len(argv) > 7 else 0
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
MODEL = os.path.join(WORK, "export")

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


def material(name, color, rough, metal, normal, ao=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(path, colour):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path, check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    nt.links.new(tex(color, True).outputs[0], b.inputs["Base Color"])
    nt.links.new(tex(rough, False).outputs[0], b.inputs["Roughness"])
    nt.links.new(tex(metal, False).outputs[0], b.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(normal, False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def load_obj(path, mat, swap):
    positions, uvs, normals = [], [], []
    polys = []
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
    ob = bpy.data.objects.new(mesh.name, mesh)
    scene.collection.objects.link(ob)
    return ob


shown = {}
if "old" in WHICH:
    d = os.path.join(WORK, "old")
    mat = material("old", os.path.join(d, "old_color.png"), os.path.join(d, "old_rough.png"), os.path.join(d, "old_metal.png"), os.path.join(d, "old_normal_gl.png"))
    # LOD 0 of the old model's three body groups, as mask 11 shows them.
    shown["before"] = [load_obj(os.path.join(d, f"old_mesh_{k}.obj"), mat, False) for k in (0, 4, 8)]
if "new" in WHICH:
    d = MODEL
    mat = material("new", os.path.join(d, "flashbang_color.png"), os.path.join(d, "flashbang_rough.png"), os.path.join(d, "flashbang_metal.png"), os.path.join(d, "flashbang_normal.png"))
    groups = ("grenade", "spoon", "pin")
    files = [os.path.join(d, f"flashbang_{g}_lod{min(LOD, 1) if g == 'pin' else LOD}.obj") for g in groups]
    shown["after"] = [load_obj(f, mat, True) for f in files]

# A plain gun-mat table in a dim room: the same for both.
floor = bpy.data.meshes.new("floor")
floor.from_pydata([(-200, -200, 0), (200, -200, 0), (200, 200, 0), (-200, 200, 0)], [], [(0, 1, 2, 3)])
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
fb = fm.node_tree.nodes["Principled BSDF"]
fb.inputs["Base Color"].default_value = (0.05, 0.05, 0.048, 1)
fb.inputs["Roughness"].default_value = 0.62
floor.materials.append(fm)
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)
fo.hide_render = False

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
so.rotation_euler = Vector((0.75, -0.95, 0.85)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 0.05
cam.clip_end = 5000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: eye, target, lens, aspect. Z is up; the lever runs down the -X side and the pull ring hangs off +Y.
VIEWS = {
    "front": ((11.5, -10.0, 5.2), (0, 0, 2.7), 70, 1.0),
    "lever": ((-11.5, -8.8, 5.8), (-0.1, 0, 2.7), 70, 1.0),
    "pin": ((-3.4, 9.4, 7.0), (-0.2, 0.1, 4.2), 80, 1.0),
    "top": ((-2.8, -3.2, 8.6), (-0.1, 0.05, 4.7), 85, 1.0),
    "ports": ((6.8, -5.8, 3.0), (0, 0, 2.2), 70, 1.0),
    "rear": ((-11.5, 10.0, 5.2), (0, 0, 2.7), 70, 1.0),
    "base": ((7.0, -8.0, -0.5), (0, 0, 2.2), 70, 1.0),
    "lodview": ((11.5, -10.0, 5.2), (0, 0, 2.7), 120, 1.0),
    "picture": ((13.5, -11.5, 6.4), (-0.15, 0, 2.72), 84, 1.0),  # The skin picker's pictures: no table, transparent.
}
for name in WANTED:
    eye, target, lens, aspect = VIEWS[name]
    if name == "picture":
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = "RGBA"
        fo.hide_render = True
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant in shown:
        for key, obs in shown.items():
            for ob in obs:
                ob.hide_render = key != variant
        suffix = f"-lod{LOD}" if LOD else ""
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}{suffix}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
print("renders done", flush=True)
