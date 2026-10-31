"""Matched Cycles renders of Boxyard's bomb site B drums, old and new, where the map puts them: same camera, light and exposure, on the
yard's own concrete. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_oil_drum.py -- <project root> <out dir> <width> <samples> <views> [old,new] [lod]
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
MODEL = os.path.join(ASSETS, "models/maps/boxyard/oil_drum_v2")
PROPS = os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj")
# boxyard_map's B site drums: (e, n, paint), which are engine (n, -e). The yaw only turns the new drum: it isn't in the old mesh.
DRUMS = ((557.0, -498.0, "blue", 200.0), (592.0, -515.0, "red", 160.0), (562.0, -534.0, "blue", 75.0))
CENTRE = (-515.0, -570.0)

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


def flat(name, tint, rough, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return mat


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
    """An old bx_ paint: its maps where it has them, its tint and flat values where it doesn't."""
    text = open(os.path.join(ASSETS, f"materials/boxyard/{paint}.vmat"), encoding="utf-8").read()
    keys = dict(re.findall(r'(\w+)\s+"([^"]+)"', text))
    metal = float(keys.get("g_flMetalness", "0"))
    colour = keys.get("TextureColor", "")
    if colour.startswith("materials/boxyard"):
        return textured(paint, os.path.join(ASSETS, colour), os.path.join(ASSETS, keys["TextureRoughness"]), os.path.join(ASSETS, keys["TextureNormal"]), None, metal)
    tint = [float(x) for x in keys["g_vColorTint"].strip("[]").split()[:3]]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in tint]
    rough = keys.get("TextureRoughness", "[0.6").strip("[").split()[0]
    return flat(paint, linear, float(rough) if rough[0].isdigit() else 0.45, metal)


def old_drums():
    """The old drums' own faces out of the merged props model, with their own materials: the drums, and their galvanised bungs."""
    positions, uvs, normals = [], [], []
    by_paint = {}
    current = None
    for line in open(PROPS, encoding="utf-8"):
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
        elif tag == "f " and current in ("bx_drum_blue", "bx_drum_red", "bx_galv"):
            by_paint.setdefault(current, []).append([tok.split("/") for tok in line.split()[1:]])
    centres = np.array([(n, -e) for e, n, _, _ in DRUMS])
    obs = []
    for paint, polys in by_paint.items():
        vs, us, ns, idx = [], [], [], []
        for poly in polys:
            c = np.mean([positions[int(t[0]) - 1] for t in poly], axis=0)
            if np.min(np.hypot(centres[:, 0] - c[0], centres[:, 1] - c[1])) > 13.5:
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
        print("old", paint, "polys", len(idx), flush=True)
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
    shown["before"] = old_drums()
if "new" in WHICH:
    mesh = load_mesh(os.path.join(MODEL, f"oil_drum_lod{LOD}.obj"))
    obs = []
    for e, n, colour, yaw in DRUMS:
        copy = mesh.copy()
        copy.materials.append(textured(colour, os.path.join(MODEL, f"oil_drum_{colour}_color.png"), os.path.join(MODEL, "oil_drum_rough.png"), os.path.join(MODEL, "oil_drum_normal.png"), os.path.join(MODEL, "oil_drum_metal.png")))
        ob = bpy.data.objects.new(colour, copy)
        scene.collection.objects.link(ob)
        ob.location = (n, -e, 0.0)
        ob.rotation_euler = Euler((0, 0, math.radians(yaw)))
        obs.append(ob)
    shown["after"] = obs

# The yard's concrete, mapped at its real tile size, and a closed container's dark flank behind, as a backstop.
floor = bpy.data.meshes.new("floor")
S = 800.0
cx, cy = CENTRE
corners = [(cx - S, cy - S, 0), (cx + S, cy - S, 0), (cx + S, cy + S, 0), (cx - S, cy + S, 0)]
floor.from_pydata(corners, [], [(0, 1, 2, 3)])
tile = 768.0
floor.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([(-y / tile, x / tile) for x, y, _ in corners], np.float32).ravel())
base = os.path.join(ASSETS, "materials/boxyard/bx_concrete")
floor.materials.append(textured("concrete", base + "_color.jpg", base + "_rough.png", base + "_normal.jpg"))
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)
wall = bpy.data.meshes.new("wall")
wall.from_pydata([(-800, -640, 0), (-260, -640, 0), (-260, -640, 102), (-800, -640, 102)], [], [(0, 1, 2, 3)])
wall.materials.append(flat("wall", (0.05, 0.05, 0.055), 0.55))
wo = bpy.data.objects.new("wall", wall)
scene.collection.objects.link(wo)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(60))
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
so.rotation_euler = Vector((0.65, 0.85, 0.95)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: eye, target, lens, aspect. Engine axes: the site's drums are at X -498..-534, Y -557..-592, and players come from +Y.
VIEWS = {
    "site": ((-500, -478, 62), (-515, -572, 18), 34, 0.62),  # Walking onto the site from the lane.
    "close": ((-470, -522, 46), (-498, -557, 20), 40, 1.0),  # The near blue drum.
    "red": ((-468, -628, 42), (-515, -592, 19), 40, 1.0),  # The red drum, from the wall side.
    "head": ((-484, -538, 72), (-498, -557, 33), 40, 1.0),  # Down onto its head and bungs.
    "lodview": ((-500, -478, 62), (-515, -572, 18), 60, 0.5),
}
for name in WANTED:
    eye, target, lens, aspect = VIEWS[name]
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
