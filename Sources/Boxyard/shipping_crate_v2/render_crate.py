"""Matched Cycles renders of Boxyard's crates, old and new, where the map puts them: same camera, light and exposure, on the yard's own
concrete. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_crate.py -- <project root> <out dir> <width> <samples> <views> [old,new] [lod] [old props obj]
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
MODEL = os.path.join(ASSETS, "models/maps/boxyard/shipping_crate_v2")
PROPS = argv[7] if len(argv) > 7 else os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj")
# boxyard_props' crates: (e, n, z0, variant), engine (n, -e, z0). All these run along n, which is engine X.
CRATES = ((640.0, 544.0, 0.0, "standard"), (672.0, 544.0, 0.0, "standard"), (656.0, 544.0, 31.5, "standard"), (96.0, 207.0, 0.0, "large"))
SIZE = {"standard": (47.2, 31.5, 31.5), "large": (60.0, 48.0, 48.0)}

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


def textured(name, color, rough, normal, metal=None):
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
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(normal, False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def old_crates():
    """The old crates' own faces out of the merged props model: every rw_wood face inside one of their boxes."""
    positions, uvs, normals, polys = [], [], [], []
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
        elif tag == "f " and current == "rw_wood":
            polys.append([tok.split("/") for tok in line.split()[1:]])
    boxes = []
    for e, n, z0, variant in CRATES:
        L, W, H = SIZE[variant]
        boxes.append((n - L / 2 - 0.2, n + L / 2 + 0.2, -e - W / 2 - 0.2, -e + W / 2 + 0.2, z0 - 0.2, z0 + H + 0.2))
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        c = np.mean([positions[int(t[0]) - 1] for t in poly], axis=0)
        if not any(x0 <= c[0] <= x1 and y0 <= c[1] <= y1 and z0 <= c[2] <= z1 for x0, x1, y0, y1, z0, z1 in boxes):
            continue
        start = len(vs)
        for t in poly:
            vs.append(positions[int(t[0]) - 1])
            us.append(uvs[int(t[1]) - 1] if len(t) > 1 and t[1] else (0.0, 0.0))
            if len(t) > 2 and t[2]:
                ns.append(normals[int(t[2]) - 1])
        idx.append(tuple(range(start, start + len(poly))))
    mesh = bpy.data.meshes.new("old crates")
    mesh.from_pydata(vs, [], idx)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
    if len(ns) == len(vs):
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
    d = os.path.join(ASSETS, "materials/railhead")
    mesh.materials.append(textured("rw_wood", os.path.join(d, "rw_wood_color.png"), os.path.join(d, "wood_rough.png"), os.path.join(d, "wood_normal.png")))
    ob = bpy.data.objects.new("old crates", mesh)
    scene.collection.objects.link(ob)
    print("old crate polys", len(idx), flush=True)
    return [ob]


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
    shown["before"] = old_crates()
if "new" in WHICH:
    obs = []
    made = {}
    for k, (e, n, z0, variant) in enumerate(CRATES):
        if variant not in made:
            mesh = load_mesh(os.path.join(MODEL, f"crate_{variant}_lod{LOD}.obj"))
            stem = os.path.join(MODEL, f"crate_{variant}")
            mesh.materials.append(textured(variant, stem + "_color.png", stem + "_rough.png", stem + "_normal.png", stem + "_metal.png"))
            made[variant] = mesh
        ob = bpy.data.objects.new(f"crate {k}", made[variant])
        scene.collection.objects.link(ob)
        ob.location = (n, -e, z0)
        # Turned end for end at random in the map: this stack shows both sides.
        ob.rotation_euler = Euler((0, 0, math.radians(180.0 if k == 1 else 0.0)))
        obs.append(ob)
    shown["after"] = obs

floor = bpy.data.meshes.new("floor")
S = 1400.0
corners = [(350 - S, -350 - S, 0), (350 + S, -350 - S, 0), (350 + S, -350 + S, 0), (350 - S, -350 + S, 0)]
floor.from_pydata(corners, [], [(0, 1, 2, 3)])
tile = 768.0
floor.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([(-y / tile, x / tile) for x, y, _ in corners], np.float32).ravel())
base = os.path.join(ASSETS, "materials/boxyard/bx_concrete")
floor.materials.append(textured("concrete", base + "_color.jpg", base + "_rough.png", base + "_normal.jpg"))
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)
wall_mat = bpy.data.materials.new("wall")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.05, 0.055, 1)
wall_mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.55
for name, pts in (("wall a", [(590, -900, 0), (590, -400, 0), (590, -400, 110), (590, -900, 110)]), ("wall b", [(280, -300, 0), (280, 60, 0), (280, 60, 110), (280, -300, 110)])):
    wall = bpy.data.meshes.new(name)
    wall.from_pydata(pts, [], [(0, 1, 2, 3)])
    wall.materials.append(wall_mat)
    scene.collection.objects.link(bpy.data.objects.new(name, wall))

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
so.rotation_euler = Vector((-0.75, 0.8, 0.9)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: eye, target, lens, aspect. Engine axes. The A site stack is at X 544, Y -640 to -672; the big crate at X 207, Y -96.
VIEWS = {
    "site": ((462, -580, 62), (544, -656, 30), 36, 0.62),  # Walking onto A from the lane.
    "close": ((490, -600, 44), (532, -640, 18), 40, 1.0),  # The near crate's side and end.
    "top": ((498, -612, 88), (544, -656, 56), 40, 1.0),  # Onto the top crate's lid.
    "big": ((150, -40, 56), (207, -96, 26), 40, 1.0),  # The big crate at the end of the middle lane.
    "lodview": ((462, -580, 62), (544, -656, 30), 60, 0.5),
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
