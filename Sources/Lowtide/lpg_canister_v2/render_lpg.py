"""Matched Cycles renders of the shipped LPG models and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_lpg.py -- <project root> <out dir> <width> <samples> <views> [old|new|both]

Old materials are read from their vmats (textures, tints, metalness), new ones likewise. One ground, one sky, one sun,
one exposure, ACES 1.3. Engine axes: the bottle lies along Y, the valve at +Y, the hose side at +X, Z up.
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
WHICH = argv[5] if len(argv) > 5 else "both"
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
OLD_DIR = os.path.join(ROOT, "output/asset-improvement-20261030/lpg-canister/retired-lpg_canister")
NEW_DIR = os.path.join(ASSETS, "models/props/lowtide/lpg_canister_v2")

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
    """Any of these vmats: a texture where it names a real one, the flat value where it names the default."""
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
    return {k + ".vmat" if not k.endswith(".vmat") else k: v for k, v in re.findall(r'\{ from = "([^"]+?)(?:\.vmat)?" to = "([^"]+)" \}', doc)}


def load_model(folder, name, lod=None):
    remaps = {k.removesuffix(".vmat"): v for k, v in remaps_of(os.path.join(folder, name + ".vmdl")).items()}
    file = name + ("" if lod is None else f"_lod{lod}") + ".obj"
    return load_obj(os.path.join(folder, file), remaps)


def place(obs, location=(0, 0, 0), rotation=(0, 0, 0)):
    for ob in obs:
        ob.location = location
        ob.rotation_euler = Euler(tuple(math.radians(a) for a in rotation))


def twin(obs):
    out = []
    for ob in obs:
        copy = ob.copy()
        scene.collection.objects.link(copy)
        out.append(copy)
    return out


sets = {}
for variant, name in (("intact", "lpg_canister"), ("ruptured", "lpg_canister_ruptured"), ("cap", "lpg_canister_cap")):
    if WHICH in ("old", "both"):
        sets[variant, "before"] = load_model(OLD_DIR, name)
    if WHICH in ("new", "both"):
        sets[variant, "after"] = load_model(NEW_DIR, name, 0)
# Two poses of the end cap, one dome up and one showing its inside, side by side on the ground.
for (variant, state), obs in list(sets.items()):
    if variant == "cap":
        place(obs, (-8, 0, -6.7 + 2.2), (-90, 18, 0))
        other = twin(obs)
        place(other, (8, 0, -6.7 + 3.4), (112, 0, 24))
        sets[variant, state] = obs + other

bpy.ops.mesh.primitive_plane_add(size=5000, location=(0, 0, -6.72))
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
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(310))
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
so.rotation_euler = (Vector((-1.0, -0.55, 1.1))).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co

# name: variant, eye, target, lens, aspect. "far" is a crop of 1080p at 60 degrees, from 8 metres: what a player gets.
VIEWS = {
    "hero": ("intact", (-44, -40, 22), (0, 1.5, -1.5), 50, 0.66),
    "side": ("intact", (-66, 2, 12), (0, 1.5, -1.5), 50, 0.5),
    "valve": ("intact", (-13, 40, 10), (0, 17, -1), 50, 0.8),
    "saddle": ("intact", (-30, -24, 5), (0, -10, -3), 50, 0.7),
    "far": ("intact", (-250, -150, 60), (0, 0, -1), 150, 0.75),
    "rhero": ("ruptured", (-44, -40, 22), (0, 1.5, -1.5), 50, 0.66),
    "rside": ("ruptured", (-52, 2, 26), (0, 0, -1), 50, 0.6),
    "rend": ("ruptured", (-20, -44, 20), (0, -8, -1), 50, 0.7),
    "rvalve": ("ruptured", (-13, 40, 10), (0, 17, -1), 50, 0.8),
    "cap": ("cap", (0, -44, 20), (0, 0, -3), 50, 0.6),
}
state_of = {}
for name in WANTED:
    variant, eye, target, lens, aspect = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH if name != "far" else 400
    scene.render.resolution_y = int(scene.render.resolution_x * aspect)
    for state in ("before", "after"):
        if (variant, state) not in sets:
            continue
        for key, obs in sets.items():
            for ob in obs:
                ob.hide_render = key != (variant, state)
        scene.render.filepath = os.path.join(OUT, f"{name}-{state}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, state, flush=True)
print("renders done", flush=True)
