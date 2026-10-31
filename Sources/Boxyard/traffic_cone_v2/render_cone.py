"""Matched Cycles renders of Boxyard's two middle-lane cones, old and new, where the map puts them: same camera, light and exposure, on the
yard's own concrete. The old cones are their own faces out of the merged props model. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_cone.py -- <project root> <work dir> <out dir> <width> <samples> <views> [old,new] [lod]
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, WORK, OUT = argv[0], argv[1], argv[2]
WIDTH, SAMPLES = int(argv[3]), int(argv[4])
WANTED = argv[5].split(",")
WHICH = argv[6].split(",") if len(argv) > 6 else ["old", "new"]
LOD = int(argv[7]) if len(argv) > 7 else 0
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
MODEL = os.path.join(WORK, "export")
PROPS = os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj")
# boxyard_map's (e, n) are engine (n, -e).
STANDING = (-166.0, 54.0)
LYING = (-191.0, 45.0)
# boxyard_materials' flat paints for the old cone: sRGB and roughness.
OLD_PAINTS = {"bx_cone_orange": ((232, 86, 22), 0.55), "bx_reflective": ((232, 232, 226), 0.3), "bx_black_plastic": ((26, 26, 28), 0.65)}

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


def textured(name, color, rough, normal, metal_value=0.0):
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
    b.inputs["Metallic"].default_value = metal_value
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(normal, False).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def read_old():
    """The two cones' faces out of the merged model, by paint, and how the lying one lies."""
    positions, normals = [], []
    by_paint = {}
    current = None
    for line in open(PROPS, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split())
            positions.append((c, a, b))
        elif tag == "vn":
            a, b, c = map(float, line[3:].split())
            normals.append((c, a, b))
        elif line.startswith("usemtl"):
            current = line.split()[1]
        elif tag == "f " and current in OLD_PAINTS:
            by_paint.setdefault(current, []).append([tok.split("/") for tok in line.split()[1:]])
    obs, standing_base, lying_points = [], [], []
    for paint, polys in by_paint.items():
        vs, ns, idx = [], [], []
        for poly in polys:
            c = np.mean([positions[int(t[0]) - 1] for t in poly], axis=0)
            near_standing = math.hypot(c[0] - STANDING[0], c[1] - STANDING[1]) < 11.0
            near_lying = math.hypot(c[0] - LYING[0], c[1] - LYING[1]) < 32.0
            if not near_standing and not near_lying:
                continue
            start = len(vs)
            for t in poly:
                vs.append(positions[int(t[0]) - 1])
                if len(t) > 2 and t[2]:
                    ns.append(normals[int(t[2]) - 1])
            idx.append(tuple(range(start, start + len(poly))))
            if near_standing and paint == "bx_black_plastic":
                standing_base.extend(vs[start:])
            if near_lying and not near_standing and paint != "bx_black_plastic":
                lying_points.extend(vs[start:])
        if not idx:
            continue
        mesh = bpy.data.meshes.new(paint)
        mesh.from_pydata(vs, [], idx)
        if len(ns) == len(vs):
            mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
            mesh.normals_split_custom_set(ns)
        tint, rough = OLD_PAINTS[paint]
        mesh.materials.append(flat(paint, [linear(c) for c in tint], rough))
        ob = bpy.data.objects.new(paint, mesh)
        scene.collection.objects.link(ob)
        obs.append(ob)
        print("old", paint, "polys", len(idx), flush=True)
    return obs, np.array(standing_base), np.array(lying_points)


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
old_obs, base_points, lying_points = read_old()
# The standing cone's base turns as the old one's does, read from its bounding box's tightest turn. The lying one's axis runs base to tip.
best, yaw = 1e9, 0.0
for deg in range(0, 90):
    a = math.radians(deg)
    x = base_points[:, 0] * math.cos(a) + base_points[:, 1] * math.sin(a)
    y = -base_points[:, 0] * math.sin(a) + base_points[:, 1] * math.cos(a)
    area = (x.max() - x.min()) * (y.max() - y.min())
    if area < best:
        best, yaw = area, a
tilt = math.atan2(6.0, 28.0)
centred = lying_points - lying_points.mean(0)
axis = Vector(np.linalg.svd(centred, full_matrices=False)[2][0].tolist())
# The tip is the narrower end. The old cone's axis climbs, leaving its tip in the air, so the new one tilts down to rest on the ground.
ends = centred @ np.array(axis)
spread = np.linalg.norm(centred - np.outer(ends, np.array(axis)), axis=1)
if spread[ends > ends.mean()].mean() > spread[ends < ends.mean()].mean():
    axis = -axis
heading = Vector((axis.x, axis.y)).normalized()
axis = Vector((heading.x * math.cos(tilt), heading.y * math.cos(tilt), -math.sin(tilt)))
# Back 3 in along its heading, or the tip, now down on the ground, would go into the crate behind it.
lying_base = Vector((LYING[0] - heading.x * 3.0, LYING[1] - heading.y * 3.0, 7.0 * math.cos(tilt)))
print("yaw", math.degrees(yaw), "lying axis", tuple(round(c, 3) for c in axis), flush=True)

if "old" in WHICH:
    shown["before"] = old_obs
else:
    for ob in old_obs:
        ob.hide_render = True
if "new" in WHICH:
    mesh = load_mesh(os.path.join(MODEL, f"traffic_cone_lod{LOD}.obj"))
    mesh.materials.append(textured("cone", os.path.join(MODEL, "traffic_cone_color.png"), os.path.join(MODEL, "traffic_cone_rough.png"), os.path.join(MODEL, "traffic_cone_normal.png")))
    standing = bpy.data.objects.new("standing", mesh)
    scene.collection.objects.link(standing)
    standing.location = (STANDING[0], STANDING[1], 0.0)
    standing.rotation_euler = Euler((0, 0, yaw))
    lying = bpy.data.objects.new("lying", mesh)
    scene.collection.objects.link(lying)
    lying.location = lying_base
    lying.rotation_mode = "QUATERNION"
    lying.rotation_quaternion = axis.to_track_quat("Z", "Y")
    shown["after"] = [standing, lying]

# The yard's concrete, mapped at its real tile size, and a dark container flank behind, as a backstop.
floor = bpy.data.meshes.new("floor")
S = 800.0
cx, cy = STANDING
corners = [(cx - S, cy - S, 0), (cx + S, cy - S, 0), (cx + S, cy + S, 0), (cx - S, cy + S, 0)]
floor.from_pydata(corners, [], [(0, 1, 2, 3)])
tile = 768.0
floor.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array([(-y / tile, x / tile) for x, y, _ in corners], np.float32).ravel())
base = os.path.join(ASSETS, "materials/boxyard/bx_concrete")
floor.materials.append(textured("concrete", base + "_color.jpg", base + "_rough.png", base + "_normal.jpg"))
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)
wall = bpy.data.meshes.new("wall")
wall.from_pydata([(-500, 150, 0), (100, 150, 0), (100, 150, 102), (-500, 150, 102)], [], [(0, 1, 2, 3)])
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
so.rotation_euler = Vector((0.65, -0.85, 0.95)).to_track_quat("Z", "Y").to_euler()

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
sx, sy = STANDING
# name: eye, target, lens, aspect.
VIEWS = {
    "pair": ((sx + 6, sy - 76, 48), (sx - 12, sy + 2, 9), 42, 0.7),  # Walking up the lane towards them.
    "close": ((sx + 24, sy - 36, 30), (sx, sy, 14.5), 50, 1.0),
    "sleeve": ((sx + 15, sy - 21, 24), (sx, sy, 17), 60, 1.0),
    "base": ((sx + 15, sy - 19, 15), (sx, sy, 2.5), 62, 1.0),
    "tip": ((sx + 6, sy - 10, 40), (sx, sy, 25), 62, 1.0),
    "lying": ((LYING[0] + 30, LYING[1] - 28, 22), (LYING[0] - 11, LYING[1] + 1, 6), 50, 1.0),
    "lodview": ((sx + 6, sy - 76, 48), (sx - 12, sy + 2, 9), 60, 0.5),
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
