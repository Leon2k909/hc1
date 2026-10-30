"""All four LODs side by side from their exported OBJs, to see that each one holds its shape and its atlas.

blender -b --factory-startup -t 2 --python render_lods.py -- <project root> <out png> <width> <samples>
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
ASSETS = os.path.join(ROOT, "Assets")
MODEL = os.path.join(ASSETS, "models/gameplay/capture_flag_v2")
TINT = (0.775, 0.0144, 0.0212, 1.0)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.view_settings.view_transform = "ACES 1.3"
scene.view_settings.exposure = -0.2


def keys_of(rel):
    keys = {}
    for line in open(os.path.join(ASSETS, rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


cache = {}


def material(rel):
    if rel in cache:
        return cache[rel]
    keys = keys_of(rel)
    mat = bpy.data.materials.new(os.path.basename(rel))
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def tex(path, colour):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(ASSETS, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    colour = tex(keys["TextureColor"], True)
    if float(keys.get("g_flModelTintAmount", "0")) > 0:
        mult = nt.nodes.new("ShaderNodeMixRGB")
        mult.blend_type = "MULTIPLY"
        mult.inputs[0].default_value = 1
        nt.links.new(colour.outputs[0], mult.inputs[1])
        mult.inputs[2].default_value = TINT
        nt.links.new(mult.outputs[0], bsdf.inputs["Base Color"])
    else:
        nt.links.new(colour.outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(tex(keys["TextureRoughness"], False).outputs[0], bsdf.inputs["Roughness"])
    if "TextureMetalness" in keys:
        nt.links.new(tex(keys["TextureMetalness"], False).outputs[0], bsdf.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(keys["TextureNormal"], False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    if "TextureTranslucency" in keys:
        cut = nt.nodes.new("ShaderNodeMath")
        cut.operation = "GREATER_THAN"
        cut.inputs[1].default_value = 0.5
        nt.links.new(tex(keys["TextureTranslucency"], False).outputs[0], cut.inputs[0])
        nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
    cache[rel] = mat
    return mat


doc = open(os.path.join(MODEL, "capture_flag.vmdl"), encoding="utf-8").read()
remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', doc))


def load(lod, offset):
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
    for line in open(os.path.join(MODEL, f"capture_flag_lod{lod}.obj"), encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split())
            positions.append((c + offset, a, b))
        elif tag == "vt":
            uvs.append(tuple(map(float, line[3:].split())))
        elif tag == "vn":
            a, b, c = map(float, line[3:].split())
            normals.append((c, a, b))
        elif line.startswith("usemtl"):
            current = line.split()[1]
            faces.setdefault(current, [])
        elif tag == "f ":
            faces[current].append([tuple(int(i) - 1 for i in tok.split("/")) for tok in line.split()[1:]])
    for paint, tris in faces.items():
        vs, us, ns, idx = [], [], [], []
        for tri in tris:
            start = len(vs)
            for v, t, n in tri:
                vs.append(positions[v])
                us.append(uvs[t])
                ns.append(normals[n])
            idx.append((start, start + 1, start + 2))
        mesh = bpy.data.meshes.new(f"lod{lod}_{paint}")
        mesh.from_pydata(vs, [], idx)
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
        mesh.materials.append(material(remaps[paint]))
        ob = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(ob)
    print("lod", lod, "tris", sum(len(t) for t in faces.values()), flush=True)


for lod in range(4):
    load(lod, lod * 105.0)

bpy.ops.mesh.primitive_plane_add(size=4000, location=(150, 0, -0.01))
ground = bpy.context.object
gm = bpy.data.materials.new("ground")
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.08, 0.065, 1)
gm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
ground.data.materials.append(gm)
world = bpy.data.worlds.new("sky")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.72, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.4
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(49), 0, math.radians(-38))
cam = bpy.data.cameras.new("c")
cam.lens = 50
cam.clip_end = 20000
co = bpy.data.objects.new("c", cam)
scene.collection.objects.link(co)
scene.camera = co
target = Vector((165, 0, 48))
co.location = target + Vector((40, -700, 26))
co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
scene.render.resolution_x = WIDTH
scene.render.resolution_y = int(WIDTH * 0.42)
scene.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("lods rendered", flush=True)
