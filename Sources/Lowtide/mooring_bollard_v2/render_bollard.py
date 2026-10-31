"""Matched Cycles renders of Lowtide's quay bollards, old and new, where the map puts them: same camera, light and exposure. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_bollard.py -- <project root> <out dir> <width> <samples> <views> [old,new] [lod]
"""
import glob
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
MODEL = os.path.join(ASSETS, "models/maps/lowtide/mooring_bollard_v2")
DRESS = [os.path.join(ASSETS, f"models/maps/lowtide/lowtide_dress_{side}.obj") for side in ("east", "west")]
# lowtide_map: mooring_bollard( m, s * e, QUAY_N + 20 ) for e 360, 690, 1020... The harbour is at n below -1600, which is engine -X.
QUAY_X = -1580.0
SPOTS = ((-690.0, 15.0), (-1020.0, 130.0))

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
    if isinstance(rough, float):
        b.inputs["Roughness"].default_value = rough
    else:
        nt.links.new(tex(rough, False).outputs[0], b.inputs["Roughness"])
    if metal:
        nt.links.new(tex(metal, False).outputs[0], b.inputs["Metallic"])
    else:
        b.inputs["Metallic"].default_value = metal_value
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(normal, False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def from_vmat(rel):
    keys = dict(re.findall(r'(\w+)\s+"([^"]+)"', open(os.path.join(ASSETS, rel), encoding="utf-8").read()))
    a = lambda k: os.path.join(ASSETS, keys[k])
    # A vmat can give a flat value in place of a map, as "[0.7 0.7 0.7 0]".
    rough = float(keys["TextureRoughness"].strip("[").split()[0]) if keys["TextureRoughness"].startswith("[") else a("TextureRoughness")
    return textured(rel, a("TextureColor"), rough, a("TextureNormal"), None, float(keys.get("g_flMetalness", "0")))


def old_bollards():
    """The old bollards' own faces out of the merged dressing: iron_black within each one's box."""
    centres = np.array([(QUAY_X, y) for y, _ in SPOTS])
    vs, us, ns, idx = [], [], [], []
    for path in DRESS:
        if not os.path.exists(path):
            continue
        positions, uvs, normals = [], [], []
        current = None
        for line in open(path, encoding="utf-8", errors="ignore"):
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
            elif tag == "f " and current == "iron_black":
                poly = [tok.split("/") for tok in line.split()[1:]]
                c = np.mean([positions[int(t[0]) - 1] for t in poly], axis=0)
                if c[2] > 26.0 or np.min(np.hypot(centres[:, 0] - c[0], centres[:, 1] - c[1])) > 10.0:
                    continue
                start = len(vs)
                for t in poly:
                    vs.append(positions[int(t[0]) - 1])
                    us.append(uvs[int(t[1]) - 1] if len(t) > 1 and t[1] else (0.0, 0.0))
                    if len(t) > 2 and t[2]:
                        ns.append(normals[int(t[2]) - 1])
                idx.append(tuple(range(start, start + len(poly))))
    print("old bollard polys", len(idx), flush=True)
    mesh = bpy.data.meshes.new("old")
    mesh.from_pydata(vs, [], idx)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
    if len(ns) == len(vs):
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
    mesh.materials.append(from_vmat("materials/buildings/iron_black.vmat"))
    ob = bpy.data.objects.new("old", mesh)
    scene.collection.objects.link(ob)
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
    shown["before"] = old_bollards()
if "new" in WHICH:
    mesh = load_mesh(os.path.join(MODEL, f"mooring_bollard_lod{LOD}.obj"))
    stem = os.path.join(MODEL, "mooring_bollard")
    mesh.materials.append(textured("new", stem + "_color.png", stem + "_rough.png", stem + "_normal.png", stem + "_metal.png"))
    obs = []
    for y, yaw in SPOTS:
        ob = bpy.data.objects.new("bollard", mesh)
        scene.collection.objects.link(ob)
        ob.location = (QUAY_X, y, 0.0)
        ob.rotation_euler = Euler((0, 0, math.radians(yaw)))
        obs.append(ob)
    shown["after"] = obs

# The quay's granite to its edge, then the harbour below it.
granite = next(iter(glob.glob(os.path.join(ASSETS, "materials/lowtide/**/lt_tidal_granite.vmat"), recursive=True)), None)
floor = bpy.data.meshes.new("quay")
corners = [(-1600, -1700, 0), (-300, -1700, 0), (-300, 300, 0), (-1600, 300, 0)]
floor.from_pydata(corners, [], [(0, 1, 2, 3)])
floor.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([(y / 128.0, x / 128.0) for x, y, _ in corners], np.float32).ravel())
floor.materials.append(from_vmat(os.path.relpath(granite, ASSETS).replace(os.sep, "/")))
scene.collection.objects.link(bpy.data.objects.new("quay", floor))
water = bpy.data.meshes.new("harbour")
water.from_pydata([(-5000, -5000, -60), (-1600, -5000, -60), (-1600, 5000, -60), (-5000, 5000, -60)], [], [(0, 1, 2, 3)])
wm = bpy.data.materials.new("harbour")
wm.use_nodes = True
wm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.05, 0.05, 1)
wm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.16
water.materials.append(wm)
scene.collection.objects.link(bpy.data.objects.new("harbour", water))
edge = bpy.data.meshes.new("wall")
edge.from_pydata([(-1600, -1700, -60), (-1600, 300, -60), (-1600, 300, 0), (-1600, -1700, 0)], [], [(0, 1, 2, 3)])
edge.materials.append(floor.materials[0])
scene.collection.objects.link(bpy.data.objects.new("wall", edge))

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
bg.inputs[1].default_value = 0.8
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.0
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((0.7, 0.75, 0.9)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: eye, target, lens, aspect. Engine axes. Standing on the quay and looking along it, past the first bollard to the next.
VIEWS = {
    "quay": ((-1506, -628, 62), (-1580, -760, 12), 34, 0.62),
    "close": ((-1548, -664, 26), (-1580, -690, 12.5), 42, 1.0),
    "harbour": ((-1612, -660, 34), (-1580, -690, 12.5), 42, 1.0),  # Its rope-worn side, seen from over the water.
    "top": ((-1552, -668, 56), (-1580, -690, 20), 42, 1.0),
    "lodview": ((-1506, -628, 62), (-1580, -690, 12), 70, 0.5),
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
