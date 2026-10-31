"""Matched Cycles renders of a Reef Hall rotunda bench, old and new, where the map puts it: same camera, light and exposure. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_bench.py -- <project root> <out dir> <width> <samples> <views> [old,new] [lod]
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, OUT = argv[0], argv[1]
WIDTH, SAMPLES = int(argv[2]), int(argv[3])
WANTED = argv[4].split(",")
WHICH = argv[5].split(",") if len(argv) > 5 else ["old", "new"]
LOD = int(argv[6]) if len(argv) > 6 else 0
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
MODEL = os.path.join(ASSETS, "models/maps/reefhall/bench_v2")
ROTUNDA = os.path.join(ASSETS, "models/maps/reefhall/reefhall_rotunda.obj")
# reefhall_map's rotunda bench at polar( 205, 420 ), yaw a + 90: engine (n, -e), and engine yaw is map yaw - 90.
ANGLE = 205.0
E, N = 420.0 * math.cos(math.radians(ANGLE)), 420.0 * math.sin(math.radians(ANGLE))
CENTRE = Vector((N, -E, 0.0))
YAW = ANGLE + 90.0 - 90.0
ALONG = Vector((math.cos(math.radians(YAW)), math.sin(math.radians(YAW)), 0.0))
FRONT = Vector((-math.sin(math.radians(YAW)), math.cos(math.radians(YAW)), 0.0))

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


def textured(name, color, rough, normal, metal=None, metal_value=0.0):
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
    if metal:
        nt.links.new(tex(metal, False).outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = metal_value
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(normal, False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def old_material(paint):
    text = open(os.path.join(ASSETS, f"materials/reefhall/{paint}.vmat"), encoding="utf-8").read()
    keys = dict(re.findall(r'(\w+)\s+"([^"]+)"', text))
    a = lambda k: os.path.join(ASSETS, keys[k])
    return textured(paint, a("TextureColor"), a("TextureRoughness"), a("TextureNormal"), None, float(keys.get("g_flMetalness", "0")))


def old_bench():
    """The old bench's own faces out of the merged rotunda model."""
    positions, uvs, normals = [], [], []
    by_paint = {}
    current = None
    for line in open(ROTUNDA, encoding="utf-8"):
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
        elif tag == "f " and current in ("rh_laminate", "rh_gunmetal"):
            by_paint.setdefault(current, []).append([tok.split("/") for tok in line.split()[1:]])
    obs = []
    for paint, polys in by_paint.items():
        vs, us, ns, idx = [], [], [], []
        for poly in polys:
            c = Vector(np.mean([positions[int(t[0]) - 1] for t in poly], axis=0))
            local = c - CENTRE
            if abs(local.dot(ALONG)) > 48.5 or abs(local.dot(FRONT)) > 9.5 or c.z > 18.5 or c.z < -0.5:
                continue
            start = len(vs)
            for t in poly:
                vs.append(positions[int(t[0]) - 1])
                us.append(uvs[int(t[1]) - 1] if len(t) > 1 and t[1] else (0.0, 0.0))
                if len(t) > 2 and t[2]:
                    ns.append(normals[int(t[2]) - 1])
            idx.append(tuple(range(start, start + len(poly))))
        if not idx:
            continue
        mesh = bpy.data.meshes.new(paint)
        mesh.from_pydata(vs, [], idx)
        mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
        if len(ns) == len(vs):
            mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
            mesh.normals_split_custom_set(ns)
        mesh.materials.append(old_material(paint))
        ob = bpy.data.objects.new(paint, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
        co_ = np.array(vs)
        print("old", paint, "polys", len(idx), "bounds", co_.min(0).round(1).tolist(), co_.max(0).round(1).tolist(), flush=True)
    return obs


def load_mesh(path):
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
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
    mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
    mesh.normals_split_custom_set(ns)
    return mesh


shown = {}
if "old" in WHICH:
    shown["before"] = old_bench()
if "new" in WHICH:
    mesh = load_mesh(os.path.join(MODEL, f"bench_lod{LOD}.obj"))
    stem = os.path.join(MODEL, "bench")
    mesh.materials.append(textured("bench", stem + "_color.png", stem + "_rough.png", stem + "_normal.png", stem + "_metal.png"))
    ob = bpy.data.objects.new("bench", mesh)
    scene.collection.objects.link(ob)
    ob.location = CENTRE
    ob.rotation_euler = Euler((0, 0, math.radians(YAW)))
    shown["after"] = [ob]

# The hall's floor at a tile size near its real one, and the dark wall of the big tank behind, with its blue glow.
floor = bpy.data.meshes.new("floor")
S = 900.0
cx, cy = CENTRE.x, CENTRE.y
corners = [(cx - S, cy - S, 0), (cx + S, cy - S, 0), (cx + S, cy + S, 0), (cx - S, cy + S, 0)]
floor.from_pydata(corners, [], [(0, 1, 2, 3)])
tile = 256.0
floor.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([(-y / tile, x / tile) for x, y, _ in corners], np.float32).ravel())
text = open(os.path.join(ASSETS, "materials/reefhall/rh_floor.vmat"), encoding="utf-8").read()
keys = dict(re.findall(r'(\w+)\s+"([^"]+)"', text))
floor.materials.append(textured("floor", os.path.join(ASSETS, keys["TextureColor"]), os.path.join(ASSETS, keys["TextureRoughness"]), os.path.join(ASSETS, keys["TextureNormal"])))
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)

back = bpy.data.materials.new("glow")
back.use_nodes = True
nt = back.node_tree
b = nt.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.01, 0.02, 0.03, 1)
b.inputs["Emission Color"].default_value = (0.03, 0.2, 0.34, 1)
b.inputs["Emission Strength"].default_value = 1.2
behind = CENTRE - FRONT * 90
wall = bpy.data.meshes.new("wall")
points = [behind - ALONG * 500, behind + ALONG * 500, behind + ALONG * 500 + Vector((0, 0, 260)), behind - ALONG * 500 + Vector((0, 0, 260))]
wall.from_pydata([tuple(p) for p in points], [], [(0, 1, 2, 3)])
wall.materials.append(back)
scene.collection.objects.link(bpy.data.objects.new("wall", wall))

world = bpy.data.worlds.new("hall")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.2, 0.25, 0.32, 1)
bg.inputs[1].default_value = 0.42
scene.world = world
for name, direction, colour, energy, angle in (
    ("downlight", Vector((0.25, 0.3, 1.0)), (1.0, 0.9, 0.76), 2.2, 9.0),
    ("tank", Vector(tuple(-FRONT)) + Vector((0, 0, 0.45)), (0.36, 0.64, 1.0), 1.1, 22.0),
):
    sun = bpy.data.lights.new(name, "SUN")
    sun.energy = energy
    sun.angle = math.radians(angle)
    sun.color = colour
    so = bpy.data.objects.new(name, sun)
    scene.collection.objects.link(so)
    so.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co


def at(along, front, z):
    return CENTRE + ALONG * along + FRONT * front + Vector((0, 0, z))


# name: eye, target, lens, aspect, seen from the front of the bench.
VIEWS = {
    "whole": (at(62, 112, 62), at(0, 0, 12), 36, 0.62),
    "end": (at(66, 36, 30), at(38, 0, 11), 38, 1.0),
    "seat": (at(14, 26, 44), at(6, 0, 17), 38, 1.0),
    "lodview": (at(62, 112, 62), at(0, 0, 12), 60, 0.5),
}
for name in WANTED:
    eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (target - eye).to_track_quat("-Z", "Y").to_euler()
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
