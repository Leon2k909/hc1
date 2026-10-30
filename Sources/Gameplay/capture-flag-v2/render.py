"""Matched Cycles renders of the shipped flag and the new one's exported files. These are not engine screenshots.

blender -b --factory-startup -t 2 --python render.py -- <project root> <out dir> <width> <samples> <views, comma separated> [tint name]

Both models stand on the same ground under the same sky, sun, cameras and exposure. The old one uses its FBX and the
values in its three vmats; the new one is read back from its OBJ, MTL names and vmats, so what's shown is what's written.
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, OUT = argv[0], argv[1]
WIDTH, SAMPLES = int(argv[2]), int(argv[3])
WANTED = argv[4].split(",")
TINT_NAME = argv[5] if len(argv) > 5 else "red"
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")

# The two team colours from TeamComponent.GetColor, linear; a flag nobody holds is white.
TINTS = {"red": (228, 32, 40), "blue": (5, 146, 235), "white": (255, 255, 255)}


def to_linear(v):
    v = v / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


TINT = tuple(to_linear(c) for c in TINTS[TINT_NAME]) + (1.0,)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.02
scene.cycles.use_denoising = True
scene.cycles.denoiser = "OPENIMAGEDENOISE"
scene.cycles.max_bounces = 5
scene.cycles.diffuse_bounces = 3
scene.cycles.glossy_bounces = 3
scene.cycles.transparent_max_bounces = 8
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"


def view_transform():
    # The game's camera tonemaps with ACES, so use it where this Blender has it.
    for name in ("ACES 1.3", "ACES 2.0", "ACES", "Filmic", "AgX"):
        try:
            scene.view_settings.view_transform = name
            return name
        except TypeError:
            continue
    return scene.view_settings.view_transform


print("view transform", view_transform(), flush=True)
if scene.view_settings.view_transform == "Filmic":
    for look in ("Filmic - Medium High Contrast", "Medium High Contrast"):
        try:
            scene.view_settings.look = look
            break
        except TypeError:
            continue
scene.view_settings.exposure = -0.2


def image(path, colour):
    img = bpy.data.images.load(os.path.join(ASSETS, path), check_existing=True)
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def parse_vmat(rel):
    keys = {}
    for line in open(os.path.join(ASSETS, rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def new_material(rel, tint=None):
    keys = parse_vmat(rel)
    mat = bpy.data.materials.new(os.path.basename(rel))
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"

    def tex(path, colour):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = image(path, colour)
        n.interpolation = "Cubic"
        nt.links.new(uv.outputs[0], n.inputs[0])
        return n

    colour = tex(keys["TextureColor"], True)
    if float(keys.get("g_flModelTintAmount", "0")) > 0 and tint:
        mult = nt.nodes.new("ShaderNodeMixRGB")
        mult.blend_type = "MULTIPLY"
        mult.inputs[0].default_value = 1
        nt.links.new(colour.outputs[0], mult.inputs[1])
        mult.inputs[2].default_value = tint
        nt.links.new(mult.outputs[0], bsdf.inputs["Base Color"])
    else:
        nt.links.new(colour.outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(tex(keys["TextureRoughness"], False).outputs[0], bsdf.inputs["Roughness"])
    if "TextureMetalness" in keys:
        nt.links.new(tex(keys["TextureMetalness"], False).outputs[0], bsdf.inputs["Metallic"])
    else:
        bsdf.inputs["Metallic"].default_value = float(keys.get("g_flMetalness", "0"))
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nt.links.new(tex(keys["TextureNormal"], False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    if "TextureTranslucency" in keys:
        alpha = tex(keys["TextureTranslucency"], False)
        cut = nt.nodes.new("ShaderNodeMath")
        cut.operation = "GREATER_THAN"
        cut.inputs[1].default_value = float(keys.get("g_flAlphaTestReference", "0.5"))
        nt.links.new(alpha.outputs[0], cut.inputs[0])
        nt.links.new(cut.outputs[0], bsdf.inputs["Alpha"])
    return mat


def load_new():
    model = os.path.join(ASSETS, "models/gameplay/capture_flag_v2")
    doc = open(os.path.join(model, "capture_flag.vmdl"), encoding="utf-8").read()
    remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', doc))
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
    for line in open(os.path.join(model, "capture_flag_lod0.obj"), encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split())
            positions.append((c, a, b))
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
    obs = []
    for paint, tris in faces.items():
        vs, us, ns, idx = [], [], [], []
        for tri in tris:
            start = len(vs)
            for v, t, n in tri:
                vs.append(positions[v])
                us.append(uvs[t])
                ns.append(normals[n])
            idx.append((start, start + 1, start + 2))
        mesh = bpy.data.meshes.new("new_" + paint)
        mesh.from_pydata(vs, [], idx)
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", np.array(us, np.float32).ravel())
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
        mesh.materials.append(new_material(remaps[paint], TINT))
        ob = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
    return obs


def flat(name, colour, metal, rough=0.5, tint=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    c = tint if tint else (*[to_linear(v * 255) if False else v for v in colour], 1)
    b.inputs["Base Color"].default_value = c
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    return mat


def load_old():
    # The old model now lives only in the rollback copy.
    bpy.ops.import_scene.fbx(filepath=os.path.join(ROOT, "output/asset-improvement-20261030/capture-flag/retired-flag_pole_base/flag_pole_base.fbx"))
    pole = flat("old_pole", (0.75, 0.75, 0.75), 0.9)
    table = {
        "flag": flat("old_flag", (1, 1, 1), 0.0, tint=TINT),
        "flag_base": flat("old_base", (0.15, 0.15, 0.15), 0.8),
        "flag_pole": pole,
    }
    obs = [o for o in scene.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    # The compiled model's bounds put FBX -Y along the engine's +X, and it's 102.6 tall: 100 times Blender's import.
    turn = Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Scale(100.0, 4)
    for ob in obs:
        ob.matrix_world = turn @ ob.matrix_world
        me = ob.data
        if len(me.materials) == 0:
            # The vmdl's global default for meshes with no material.
            me.materials.append(pole)
        for i, m in enumerate(me.materials):
            key = m.name.lower().split(".")[0]
            if key in table:
                me.materials[i] = table[key]
    return obs


def ground():
    soil = os.path.join(ASSETS, "materials/forestbase")
    mat = bpy.data.materials.new("ground")
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1 / 110.0, 1 / 110.0, 1)
    nt.links.new(coord.outputs["Object"], mapping.inputs[0])

    def t(name, colour):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(soil, name), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        nt.links.new(mapping.outputs[0], n.inputs[0])
        return n

    found = {f.lower(): f for f in os.listdir(soil)}
    colour = next((found[k] for k in found if k.startswith("mud_") and "color" in k and k.endswith((".png", ".jpg"))), None)
    normal = next((found[k] for k in found if k.startswith("mud_") and "normal" in k and k.endswith((".png", ".jpg"))), None)
    rough = next((found[k] for k in found if k.startswith("mud_") and "rough" in k and k.endswith((".png", ".jpg"))), None)
    if colour:
        nt.links.new(t(colour, True).outputs[0], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (0.13, 0.11, 0.085, 1)
    # Dry ground for both models: the texture's own wet sheen would pull the eye from what's being compared.
    b.inputs["Roughness"].default_value = 0.94
    b.inputs["Specular IOR Level"].default_value = 0.25
    if normal:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.7
        nt.links.new(t(normal, False).outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    bpy.ops.mesh.primitive_plane_add(size=6000, location=(0, 0, -0.005))
    ob = bpy.context.object
    ob.name = "ground"
    ob.data.materials.append(mat)
    uv = None
    return ob


def sky():
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    studio = os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr")
    env.image = bpy.data.images.load(studio)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0, 0, math.radians(140))
    nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
    nt.links.new(mapping.outputs[0], env.inputs[0])
    nt.links.new(env.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.85
    # The courtyard lights both models, but the camera sees plain hazy sky, not a photo of a wall.
    seen = nt.nodes.new("ShaderNodeBackground")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (0.74, 0.76, 0.78, 1)
    ramp.color_ramp.elements[1].position = 0.72
    ramp.color_ramp.elements[1].color = (0.31, 0.42, 0.62, 1)
    split = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Generated"], split.inputs[0])
    up = nt.nodes.new("ShaderNodeMath")
    up.operation = "MULTIPLY_ADD"
    up.inputs[1].default_value = 0.5
    up.inputs[2].default_value = 0.5
    nt.links.new(split.outputs["Z"], up.inputs[0])
    nt.links.new(up.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs[0], seen.inputs[0])
    seen.inputs[1].default_value = 1.0
    path = nt.nodes.new("ShaderNodeLightPath")
    choose = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(path.outputs["Is Camera Ray"], choose.inputs[0])
    nt.links.new(bg.outputs[0], choose.inputs[1])
    nt.links.new(seen.outputs[0], choose.inputs[2])
    nt.links.new(choose.outputs[0], nt.nodes["World Output"].inputs[0])
    scene.world = world
    data = bpy.data.lights.new("sun", "SUN")
    data.energy = 3.4
    data.angle = math.radians(1.6)
    data.color = (1.0, 0.95, 0.88)
    sun = bpy.data.objects.new("sun", data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(49), 0, math.radians(-38))


old = load_old()
new = load_new()
ground()
sky()
cam_data = bpy.data.cameras.new("camera")
cam_data.clip_start = 1.0
cam_data.clip_end = 20000
camera = bpy.data.objects.new("camera", cam_data)
scene.collection.objects.link(camera)
scene.camera = camera

# name: eye, target, lens mm, aspect (height / width), which models
VIEWS = {
    "full": ((122, -168, 54), (10, 2, 50), 40, 1.1),
    "base": ((-30, -34, 19), (0, 1, 6.5), 42, 0.75),
    "joint": ((16, -22, 66), (0, 0, 54), 50, 1.0),
    "top": ((58, -66, 86), (19, 0, 88), 42, 0.8),
    "foot": ((18, -56, 26), (11.5, -19.5, 5), 42, 0.75),
    "distance": ((420, -520, 64), (6, 0, 50), 55, 0.62),
    "cleat": ((14, -14, 42), (3, 0, 40), 60, 1.0),
    "back": ((-116, 168, 52), (10, 2, 50), 40, 1.1),
    "hero": ((78, -118, 22), (8, 0, 56), 30, 1.1),
    "stencil": ((10, -30, 28), (0, 0, 26), 55, 1.0),
}
for name in WANTED:
    eye, target, lens, aspect = VIEWS[name]
    camera.location = eye
    camera.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        for ob in shown:
            ob.hide_render = False
        for ob in hidden:
            ob.hide_render = True
        scene.render.filepath = os.path.join(OUT, f"{name}-{TINT_NAME}-{variant}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
print("renders done", flush=True)
