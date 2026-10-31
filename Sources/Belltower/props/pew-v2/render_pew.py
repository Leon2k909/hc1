"""Matched Cycles renders of a shipped Belltower pew and v2's exported files, in one plain room. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_sofa.py -- <project root> <export dir> <out dir> <width> <samples> <views> [after]

Same camera, light, exposure and ACES 1.3 view for both, with back faces culled, as the engine does. The old pew is cut out of
Belltower's merged centre by its materials and position, and turned into this model's frame.
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, EXPORT, OUT = argv[0], argv[1], argv[2]
WIDTH, SAMPLES = int(argv[3]), int(argv[4])
WANTED = argv[5].split(",")
ONLY = argv[6] if len(argv) > 6 else ""
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
# The front row's west pew: engine X -458 to -440, Y 40 to 140, facing -X. Local (x, y) = (-449 - X, 90 - Y).
OLD_AT = (-449.0, 90.0)
OLD_MATERIALS = ("planks", "planks_dark")

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "ACES 1.3"
scene.view_settings.exposure = -0.3


def vmat_keys(path):
    keys = {}
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def numbers(text):
    return [float(x) for x in text.strip("[] ").split()]


def material(vmat_path, root):
    """Maps where the vmat has them, its flat tint and values where it doesn't, and back faces culled."""
    keys = vmat_keys(vmat_path)
    mat = bpy.data.materials.new(os.path.basename(vmat_path))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(key, colour):
        path = keys.get(key, "")
        if path.startswith("[") or not path or not os.path.exists(os.path.join(root, path)):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(root, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    c = tex("TextureColor", True)
    if c:
        nt.links.new(c.outputs[0], b.inputs["Base Color"])
    elif "g_vColorTint" in keys:
        srgb = numbers(keys["g_vColorTint"])[:3]
        linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in srgb]
        b.inputs["Base Color"].default_value = (*linear, 1)
    r = tex("TextureRoughness", False)
    if r:
        nt.links.new(r.outputs[0], b.inputs["Roughness"])
    elif keys.get("TextureRoughness", "").startswith("["):
        b.inputs["Roughness"].default_value = numbers(keys["TextureRoughness"])[0]
    m = tex("TextureMetalness", False)
    if m:
        nt.links.new(m.outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = float(keys.get("g_flMetalness", "0"))
    n = tex("TextureNormal", False)
    if n:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(n.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    out = nt.nodes["Material Output"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(clear.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def read_obj(path):
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
    return positions, uvs, normals, faces


def make_object(name, mat, polys, positions, uvs, normals, shift=(0, 0, 0)):
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        start = len(vs)
        for tok in poly:
            p = positions[int(tok[0]) - 1]
            vs.append((p[0] + shift[0], p[1] + shift[1], p[2] + shift[2]))
            us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
            if len(tok) > 2 and tok[2]:
                ns.append(normals[int(tok[2]) - 1])
        idx.append(tuple(range(start, start + len(poly))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vs, [], idx)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
    if len(ns) == len(vs):
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    return ob


def load_new():
    path = os.path.join(EXPORT, "models/props/belltower/pew_v2", "pew_lod0.obj")
    positions, uvs, normals, faces = read_obj(path)
    mat = material(os.path.join(EXPORT, "materials/belltower/pew_v2/pew.vmat"), EXPORT)
    return [make_object("new", mat, polys, positions, uvs, normals) for polys in faces.values()]


def load_old():
    positions, uvs, normals, faces = read_obj(os.path.join(ASSETS, "models/maps/belltower/belltower_centre.obj"))
    remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', open(os.path.join(ASSETS, "models/maps/belltower/belltower_centre.vmdl"), encoding="utf-8").read()))
    cx, cy = OLD_AT

    def in_sofa(poly):
        for tok in poly:
            x, y, z = positions[int(tok[0]) - 1]
            if not (abs(x - cx) < 9.2 and abs(y - cy) < 50.2 and z < 38.2):
                return False
        return True

    obs = []
    for name in OLD_MATERIALS:
        kept = [poly for poly in faces.get(name, []) if in_sofa(poly)]
        print("old", name, len(kept), flush=True)
        if kept:
            obs.append(make_object("old_" + name, material(os.path.join(ASSETS, remaps[name]), ASSETS), kept, [(cx - p[0], cy - p[1], p[2]) for p in positions], uvs, [(-n[0], -n[1], n[2]) for n in normals]))
    return obs


def slab(name, lo, hi, colour, rough=0.85):
    mesh = bpy.data.meshes.new(name)
    x0, a0, b0 = lo
    x1, a1, b1 = hi
    v = [(x0, a0, b0), (x1, a0, b0), (x1, a1, b0), (x0, a1, b0), (x0, a0, b1), (x1, a0, b1), (x1, a1, b1), (x0, a1, b1)]
    mesh.from_pydata(v, [], [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    mesh.materials.append(m)
    scene.collection.objects.link(bpy.data.objects.new(name, mesh))


# A plain stone floor, lit from the windows' side.
slab("floor", (-800, -800, -2), (800, 800, 0), (0.34, 0.31, 0.27), 0.45)
world = bpy.data.worlds.new("sky")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.74, 0.76, 0.82, 1)
bg.inputs[1].default_value = 0.7
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 2.6
sun.angle = math.radians(8.0)
sun.color = (1.0, 0.93, 0.84)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((0.72, -0.44, 0.62)).to_track_quat("Z", "Y").to_euler()
cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co


def aim(eye, target, lens, aspect):
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)


old = load_old()
new = load_new()
# name: eye, target, lens, aspect. A standing player's eye is 64 in up.
VIEWS = {
    "player": ((118, -96, 64), (0, 0, 18), 34, 0.62),
    "rear": ((-104, -84, 62), (-2, -6, 20), 34, 0.62),
    "end": ((48, -86, 42), (2, -44, 20), 34, 0.62),
    "back": ((-44, 18, 42), (-8, -12, 26), 34, 0.62),
}
for name in WANTED:
    aim(*VIEWS[name])
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        if ONLY == "after" and variant == "before":
            continue
        for ob in shown:
            ob.hide_render = False
        for ob in hidden:
            ob.hide_render = True
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
print("renders done", flush=True)
