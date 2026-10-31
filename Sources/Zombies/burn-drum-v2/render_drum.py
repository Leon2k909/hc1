"""Matched Cycles renders of the old drum and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_drum.py -- <project root> <work dir> <out dir> <width> <samples> <views> [lod]

The old drum is the real geometry and materials cut from Riverside's merged model (old_drum.py). The flames are MapFire's
particles, which aren't in either model, so neither render has them: the fire shows only as the light MapFire gives.
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


_materials = {}


def material(rel):
    """Maps where the vmat names them and they exist; otherwise its values. Tints are sRGB, as the map's script writes them."""
    if rel in _materials:
        return _materials[rel]
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
    if "F_SELF_ILLUM" in keys:
        bright = float(keys.get("g_flSelfIllumBrightness", "1"))
        mask = tex("TextureSelfIllumMask", False)
        if mask and colour:
            times = nt.nodes.new("ShaderNodeVectorMath")
            times.operation = "MULTIPLY"
            nt.links.new(colour.outputs[0], times.inputs[0])
            nt.links.new(mask.outputs[0], times.inputs[1])
            nt.links.new(times.outputs[0], b.inputs["Emission Color"])
        else:
            b.inputs["Emission Color"].default_value = (*tint, 1)
        b.inputs["Emission Strength"].default_value = bright
    # The engine culls backfaces and Cycles doesn't, which hides faults: make a face's back transparent, as in the game.
    output = nt.nodes["Material Output"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    both = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], both.inputs[0])
    nt.links.new(b.outputs[0], both.inputs[1])
    nt.links.new(clear.outputs[0], both.inputs[2])
    nt.links.new(both.outputs[0], output.inputs["Surface"])
    _materials[rel] = mat
    return mat


def read_obj(path):
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
    return positions, uvs, normals, groups


def make_object(name, data, polys, mat, at):
    positions, uvs, normals, _ = data
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
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    ob.location = at
    return ob


old_data = read_obj(os.path.join(WORK, "old_drum.obj"))
new_data = read_obj(os.path.join(ASSETS, f"models/zombies/burn_drum_v2/burn_drum_lod{LOD}.obj"))
RS = "materials/riverside/{}.vmat"
OLD_PAINT = {"blue": "rs_drum_blue", "red": "rs_drum_red", "rust": "rs_rust", "cold": "rs_rust"}


def old_drum(variant, at):
    """The old drum in a variant, as riverside_parts.drum makes them: the body's paint swapped, and with the fire out, ash and no glowing holes."""
    obs = []
    positions = old_data[0]
    for name, polys in old_data[3].items():
        chosen, mat = polys, name
        if name == "rs_drum_blue":
            mat = OLD_PAINT[variant]
        elif name == "rs_ember" and variant == "cold":
            chosen = [p for p in polys if positions[int(p[0][0]) - 1][2] > 20]
            mat = "rs_ash"
        obs.append(make_object(f"old {variant} {name}", old_data, chosen, material(RS.format(mat)), at))
    return obs


def new_drum(variant, at):
    polys = new_data[3]["burn_drum"]
    return [make_object(f"new {variant}", new_data, polys, material(f"materials/zombies/burn_drum_v2/burn_drum_{variant}.vmat"), at)]


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
    return ob


block("ground", (-800, -800, -2), (800, 800, 0), (0.09, 0.08, 0.065), 0.9)

SETS = {"one": (("blue", (0, 0, 0)),), "row": (("blue", (0, -48, 0)), ("red", (0, -16, 0)), ("rust", (0, 16, 0)), ("cold", (0, 48, 0)))}
built = {}
for key, members in SETS.items():
    for side, maker in (("before", old_drum), ("after", new_drum)):
        built[key, side] = [ob for variant, at in members for ob in maker(variant, at)]

# Daylight, to judge the materials.
day = bpy.data.worlds.new("day")
day.use_nodes = True
nt = day.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(40))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.7
# Riverside's night: dim blue sky, a low moon.
night = bpy.data.worlds.new("night")
night.use_nodes = True
night.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.03, 0.055, 1)
night.node_tree.nodes["Background"].inputs[1].default_value = 2.2

sun = bpy.data.lights.new("sun", "SUN")
sun.angle = math.radians(1.6)
sun_ob = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(sun_ob)
fires = []
for variant, at in SETS["row"]:
    if variant == "cold":
        continue
    lamp = bpy.data.lights.new(f"fire {variant}", "POINT")
    lamp.color = (1.0, 0.5, 0.2)
    lamp.shadow_soft_size = 3.0
    ob = bpy.data.objects.new(lamp.name, lamp)
    scene.collection.objects.link(ob)
    # Where MapFire's flames are, a little over the bed.
    ob.location = (at[0], at[1], 40.0)
    fires.append(ob)
for ob in fires:
    ob.hide_render = True

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: set, eye, target, lens, aspect, night.
VIEWS = {
    "whole": ("one", (24, -80, 42), (0, 0, 16.5), 45, 1.0, False),
    "top": ("one", (22, -33, 66), (0, 0, 27), 45, 0.9, False),
    "holes": ("one", (10, -30, 9), (2, -8, 8), 34, 0.8, False),
    "row": ("row", (150, -46, 62), (0, 0, 16), 48, 0.62, False),
    "night": ("row", (130, -40, 56), (0, 0, 18), 48, 0.62, True),
    "far": ("row", (640, -180, 90), (0, 0, 20), 75, 0.5, False),
}
for name in WANTED:
    key, eye, target, lens, aspect, is_night = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    if is_night:
        scene.world = night
        # The game's exposure opens up at night, so this one does too: the same for the old drum and the new.
        scene.view_settings.exposure = 1.2
        sun.energy, sun.color = 0.55, (0.62, 0.72, 1.0)
        sun_ob.rotation_euler = Vector((0.9, -0.5, 0.42)).to_track_quat("Z", "Y").to_euler()
    else:
        scene.world = day
        scene.view_settings.exposure = -0.2
        sun.energy, sun.color = 2.6, (1.0, 0.95, 0.88)
        sun_ob.rotation_euler = Vector((1.0, -0.72, 1.05)).to_track_quat("Z", "Y").to_euler()
    for ob in fires:
        ob.hide_render = not is_night
        ob.data.energy = 9000
    for side in ("before", "after"):
        for (k, s), obs in built.items():
            for ob in obs:
                ob.hide_render = not (k == key and s == side)
        tail = f"-lod{LOD}" if LOD else ""
        scene.render.filepath = os.path.join(OUT, f"{name}-{side}{tail}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, side, flush=True)
print("renders done", flush=True)
