"""Matched Cycles renders of the shipped trolley and v2's exported files, on one concrete platform. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_trolley.py -- <project root> <out dir> <width> <samples> <views> [lods|after]

Same camera, light, exposure and ACES 1.3 view for both. Both are read from their vmdl's OBJ, vmats and textures, the way
the engine would; the old markings are alpha tested as their vmat says.
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
ONLY = argv[5] if len(argv) > 5 else ""  # "lods", or "after" to skip re-rendering the old model while reviewing.
LODS = ONLY == "lods"
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
scene.view_settings.exposure = -0.3


def vmat_keys(rel):
    keys = {}
    for line in open(os.path.join(ASSETS, rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def material(rel):
    """Maps where the vmat has them, values where it doesn't."""
    keys = vmat_keys(rel)
    mat = bpy.data.materials.new(os.path.basename(rel))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(key, colour):
        path = keys.get(key)
        if not path or not os.path.exists(os.path.join(ASSETS, path)):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(ASSETS, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    c = tex("TextureColor", True)
    if c:
        nt.links.new(c.outputs[0], b.inputs["Base Color"])
    r = tex("TextureRoughness", False)
    if r:
        nt.links.new(r.outputs[0], b.inputs["Roughness"])
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
    a = tex("TextureTranslucency", False)
    if a:
        over = nt.nodes.new("ShaderNodeMath")
        over.operation = "GREATER_THAN"
        over.inputs[1].default_value = float(keys.get("g_flAlphaTestReference", "0.5"))
        nt.links.new(a.outputs[0], over.inputs[0])
        nt.links.new(over.outputs[0], b.inputs["Alpha"])
    return mat


def load_obj(path, remaps, shift=(0, 0, 0)):
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
    for line in open(path, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split())
            positions.append((c + shift[0], a + shift[1], b + shift[2]))
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
    return dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', open(vmdl, encoding="utf-8").read()))


# A plain concrete platform, a wall behind it, and a daylight sky: the same for both.
def slab(name, lo, hi, colour, rough=0.85):
    mesh = bpy.data.meshes.new(name)
    x0, a0, b0 = lo
    x1, a1, b1 = hi
    v = [(x0, a0, b0), (x1, a0, b0), (x1, a1, b0), (x0, a1, b0), (x0, a0, b1), (x1, a0, b1), (x1, a1, b1), (x0, a1, b1)]
    mesh.from_pydata(v, [], [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 0.06
    tex.inputs["Detail"].default_value = 8.0
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.3
    ramp.inputs["From Max"].default_value = 0.7
    ramp.inputs["To Min"].default_value = 0.8
    ramp.inputs["To Max"].default_value = 1.15
    mult = nt.nodes.new("ShaderNodeVectorMath")
    mult.operation = "SCALE"
    mult.inputs[0].default_value = colour
    nt.links.new(tex.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], mult.inputs["Scale"])
    nt.links.new(mult.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    mesh.materials.append(m)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)


slab("platform", (-900, -900, -4), (900, 900, 0), (0.24, 0.235, 0.22), 0.9)
slab("wall", (-900, 330, 0), (900, 346, 400), (0.34, 0.32, 0.29), 0.9)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "sunrise.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(120))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.75
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.2
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((0.55, -0.62, 0.72)).to_track_quat("Z", "Y").to_euler()
# A soft fill from the other side, so the shaded faces can be judged too.
fill = bpy.data.lights.new("fill", "SUN")
fill.energy = 0.9
fill.angle = math.radians(30)
fill.color = (0.86, 0.92, 1.0)
fill.use_shadow = False
fo = bpy.data.objects.new("fill", fill)
scene.collection.objects.link(fo)
fo.rotation_euler = Vector((-0.35, 0.8, 0.5)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
scene.render.image_settings.color_mode = "RGB"


def aim(eye, target, lens, aspect):
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)


NEW_VMDL = os.path.join(ASSETS, "models/props/railhead/luggage_trolley_v2/luggage_trolley.vmdl")
if LODS:
    obs = []
    remaps = remaps_of(NEW_VMDL)
    for lod in range(4):
        obs += load_obj(os.path.join(os.path.dirname(NEW_VMDL), f"luggage_trolley_lod{lod}.obj"), remaps, ((lod - 1.5) * 150, 0, 0))
    aim((15, -745, 190), (15, 0, 22), 42, 0.42)
    scene.render.filepath = os.path.join(OUT, "lods.png")
    bpy.ops.render.render(write_still=True)
    print("rendered lods", flush=True)
    print("renders done", flush=True)
    sys.exit(0)

old_vmdl = os.path.join(ASSETS, "models/props/railhead/luggage/luggage_trolley.vmdl")
old = load_obj(old_vmdl.replace(".vmdl", ".obj"), remaps_of(old_vmdl))
new = load_obj(os.path.join(os.path.dirname(NEW_VMDL), "luggage_trolley_lod0.obj"), remaps_of(NEW_VMDL))
# name: eye, target, lens, aspect.
VIEWS = {
    "front": ((150, -138, 88), (14, 0, 25), 40, 0.68),
    "rear": ((-150, 130, 120), (-4, 0, 22), 40, 0.68),
    "player": ((-118, -130, 64), (-14, 0, 30), 36, 0.62),
    "crate": ((-46, -74, 54), (-30, -14, 34), 36, 0.74),
    "cases": ((-12, 66, 72), (-30, 12, 36), 36, 0.74),
    "blue": ((6, -62, 50), (-6, -14, 37), 36, 0.74),
    "wheel": ((66, -52, 22), (34, -18, 13), 36, 0.74),
    "roll": ((88, -24, 52), (38, -4, 30), 36, 0.74),
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
