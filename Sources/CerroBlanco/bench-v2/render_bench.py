"""Matched Cycles renders of the old bench, from the map's own code, and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python-exit-code 1 --python render_bench.py -- <project root> <work dir> <out dir> <width> <samples> <views>

Both stand on the same pale paving under the same sky, sun and exposure, with the ACES 1.3 view transform. The old bench's materials are
the ones the map's own files name for it.
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
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
NEW = os.path.join(ASSETS, "models", "props", "cerroblanco", "bench_v2")

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
scene.view_settings.exposure = -0.1


def material_from(vmat_rel):
    """A material from a vmat's own texture names."""
    keys = {}
    for line in open(os.path.join(ASSETS, vmat_rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"([^"]+)"\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2)
    mat = bpy.data.materials.new(os.path.basename(vmat_rel))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(key, colour):
        path = os.path.join(ASSETS, keys[key])
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path, check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    def is_map(key):
        value = keys.get(key, "")
        return bool(value) and not value.startswith("[") and "materials/default/" not in value

    # The live old teak is no texture at all: the engine's blank maps, a brown tint and one roughness. So that's what this draws.
    if is_map("TextureColor"):
        nt.links.new(tex("TextureColor", True).outputs[0], b.inputs["Base Color"])
    else:
        tint = [float(x) for x in keys.get("g_vColorTint", "[1 1 1 1]").strip("[]").split()]
        b.inputs["Base Color"].default_value = (tint[0], tint[1], tint[2], 1)
    if is_map("TextureRoughness"):
        nt.links.new(tex("TextureRoughness", False).outputs[0], b.inputs["Roughness"])
    elif keys.get("TextureRoughness", "").startswith("["):
        b.inputs["Roughness"].default_value = float(keys["TextureRoughness"].strip("[]").split()[0])
    if is_map("TextureMetalness"):
        nt.links.new(tex("TextureMetalness", False).outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = float(keys.get("g_flMetalness", "0"))
    if is_map("TextureNormal"):
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tex("TextureNormal", False).outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def load_obj(path, make):
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
    for line in open(path, encoding="utf-8", errors="ignore"):
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
            faces.setdefault(current, [])
        elif tag == "f ":
            faces[current].append([tok.split("/") for tok in line.split()[1:]])
    obs = []
    for name, polys in faces.items():
        vs, us, ns, idx = [], [], [], []
        for poly in polys:
            start = len(vs)
            for tok in poly:
                vs.append(positions[int(tok[0]) - 1])
                us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
                if len(tok) > 2 and tok[2]:
                    ns.append(normals[int(tok[2]) - 1])
            idx.append(tuple(range(start, start + len(poly))))
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vs, [], idx)
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        if len(ns) == len(vs):
            mesh.normals_split_custom_set(ns)
        else:
            mesh.set_sharp_from_angle(angle=math.radians(40))
        mesh.materials.append(make(name))
        ob = bpy.data.objects.new(name, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


old = load_obj(os.path.join(WORK, "old", "old_bench.obj"), lambda name: material_from(f"materials/cerroblanco/{name}.vmat"))
new = load_obj(os.path.join(NEW, "bench_lod0.obj"), lambda name: material_from("models/props/cerroblanco/bench_v2/bn_bench.vmat"))

bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
g = gm.node_tree.nodes["Principled BSDF"]
g.inputs["Base Color"].default_value = (0.3, 0.29, 0.27, 1)
g.inputs["Roughness"].default_value = 0.7
ground.data.materials.append(gm)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(200))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.85
seen = nt.nodes.new("ShaderNodeBackground")
seen.inputs[0].default_value = (0.46, 0.46, 0.45, 1)
path = nt.nodes.new("ShaderNodeLightPath")
choose = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(path.outputs["Is Camera Ray"], choose.inputs[0])
nt.links.new(bg.outputs[0], choose.inputs[1])
nt.links.new(seen.outputs[0], choose.inputs[2])
nt.links.new(choose.outputs[0], nt.nodes["World Output"].inputs[0])
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 2.6
sun.angle = math.radians(2.0)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((-0.6, -0.85, 1.15)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 0.5
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co

# name: eye, target, lens, aspect. The player's eyes are about 64 in up.
VIEWS = {
    "player": ((-52, -112, 64), (0, 0, 10), 36, 0.62),
    "hero": ((-96, -78, 44), (0, 0, 8), 44, 0.62),
    "seat": ((-30, -30, 34), (-8, 0, 17), 34, 0.62),
    "end": ((-72, 18, 26), (-46, 0, 10), 36, 0.75),
    "side": ((0, -86, 26), (0, 0, 9), 42, 0.5),
}
for name in [w for w in WANTED if w in VIEWS]:
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
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
if "lods" in WANTED:
    eye, target, lens, aspect = VIEWS["hero"]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for ob in old + new:
        ob.hide_render = True
    for lod in (1, 2, 3):
        obs = load_obj(os.path.join(NEW, f"bench_lod{lod}.obj"), lambda name: material_from("models/props/cerroblanco/bench_v2/bn_bench.vmat"))
        scene.render.filepath = os.path.join(OUT, f"lod{lod}.png")
        bpy.ops.render.render(write_still=True)
        for ob in obs:
            ob.hide_render = True
        print("rendered lod", lod, flush=True)
print("renders done", flush=True)
