"""Matched Cycles renders of today's dev-cube ammo case and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_ammo.py -- <project root> <out dir> <width> <samples> <views> [old|new|both]

The old case is rebuilt from `ZombiesPowerUp.CreateAmmoCase`'s own numbers, with the real magazine model. The engine's dev box
can't be read offline, so its parts are flat colours of the code's tints, which if anything flatters it.
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


_materials = {}


def material(rel):
    if rel in _materials:
        return _materials[rel]
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

    def real(key):
        return key in keys and keys[key].endswith(".png")

    tint = [float(v) for v in keys.get("g_vColorTint", "[1 1 1 1]").strip("[]").split()]
    if real("TextureColor"):
        colour = tex(keys["TextureColor"], True)
        if tint[:3] != [1.0, 1.0, 1.0]:
            scale = nt.nodes.new("ShaderNodeMixRGB")
            scale.blend_type = "MULTIPLY"
            scale.inputs[0].default_value = 1.0
            scale.inputs[2].default_value = (tint[0], tint[1], tint[2], 1)
            nt.links.new(colour.outputs[0], scale.inputs[1])
            nt.links.new(scale.outputs[0], b.inputs["Base Color"])
        else:
            nt.links.new(colour.outputs[0], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1)
    if real("TextureRoughness"):
        nt.links.new(tex(keys["TextureRoughness"], False).outputs[0], b.inputs["Roughness"])
    else:
        b.inputs["Roughness"].default_value = float(keys.get("g_flRoughnessScaleFactor", "0.6"))
    if real("TextureMetalness"):
        nt.links.new(tex(keys["TextureMetalness"], False).outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = float(keys.get("g_flMetalness", "0"))
    if real("TextureNormal"):
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex(keys["TextureNormal"], False).outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    _materials[rel] = mat
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
    doc = open(vmdl, encoding="utf-8").read()
    return {k: v for k, v in re.findall(r'\{ from = "([^"]+?)(?:\.vmat)?" to = "([^"]+)" \}', doc)}


def cube(name, center, size, tint):
    """One `AddCasePart`: a dev box scaled to size. Flat colour from the code's tint."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Roughness"].default_value = 0.6
    ob.data.materials.append(mat)
    return ob


def old_case():
    olive, dark, khaki = (0.24, 0.3, 0.12), (0.12, 0.14, 0.11), (0.55, 0.5, 0.3)
    obs = [
        cube("case", (0, 0, -3), (14, 24, 14), olive),
        cube("rim", (0, 0, 4), (15, 25, 2), dark),
        cube("handle", (-8, 0, 7), (2, 16, 2), dark),
    ]
    for y in (-8, 8):
        obs.append(cube("latch", (7.5, y, 1), (1, 3, 6), khaki))
    for y in (-7, 7):
        obs.append(cube("support", (-8, y, 4), (2, 2, 6), dark))
    folder = os.path.join(ASSETS, "attachments/rear_mag/m4a1_short_mag")
    remaps = remaps_of(os.path.join(folder, "m4a1_short_mag.vmdl"))
    base = load_obj(os.path.join(folder, "m4a1_short_mag.obj"), remaps)
    points = np.array([ob.data.vertices[i].co for ob in base for i in range(len(ob.data.vertices))])
    low, high = points.min(0), points.max(0)
    scale = 18.0 / max(high[2] - low[2], 1.0)
    centre = (low + high) / 2
    mags = list(base) + [c for _ in range(2) for c in [ob.copy() for ob in base]]
    for c in mags[len(base) :]:
        scene.collection.objects.link(c)
    for i, y in enumerate((-7.0, 0.0, 7.0)):
        for ob in mags[i * len(base) : (i + 1) * len(base)]:
            ob.scale = (scale, scale, scale)
            ob.location = (-centre[0] * scale, y - centre[1] * scale, 2 - low[2] * scale)
    return obs + mags


sets = {}
if WHICH in ("old", "both"):
    sets["before"] = old_case()
if WHICH in ("new", "both"):
    folder = os.path.join(ASSETS, "models/zombies/ammo_case_v2")
    sets["after"] = load_obj(os.path.join(folder, "ammo_case_lod0.obj"), remaps_of(os.path.join(folder, "ammo_case.vmdl")))
roots = {}
for state, obs in sets.items():
    root = bpy.data.objects.new(state, None)
    scene.collection.objects.link(root)
    for ob in obs:
        ob.parent = root
    roots[state] = root

bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -10.02))
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

# name: eye, target, lens, aspect, station. A station view is the buy station's: 2.5 times the size, 26 up from its ground.
VIEWS = {
    "hero": ((44, -38, 28), (0, 0, 2), 50, 0.8, False),
    "front": ((56, 0, 8), (0, 0, 2), 50, 0.62, False),
    "inside": ((26, -10, 38), (0, -2, 1), 50, 0.8, False),
    "back": ((-46, -30, 20), (0, 0, 3), 50, 0.72, False),
    "latch": ((22, -20, 4), (7, -8, -1.5), 50, 0.7, False),
    "far": ((260, -150, 70), (0, 0, 38), 150, 1.12, True),
}
for name in WANTED:
    eye, target, lens, aspect, station = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH if name != "far" else 400
    scene.render.resolution_y = int(scene.render.resolution_x * aspect)
    ground.location.z = 0.0 if station else -10.02
    for state, root in roots.items():
        root.scale = (2.5, 2.5, 2.5) if station else (1, 1, 1)
        root.location = (0, 0, 26) if station else (0, 0, 0)
    for state in ("before", "after"):
        if state not in sets:
            continue
        for key, obs in sets.items():
            for ob in obs:
                ob.hide_render = key != state
        scene.render.filepath = os.path.join(OUT, f"{name}-{state}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, state, flush=True)
print("renders done", flush=True)
