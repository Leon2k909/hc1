"""Blow the capture flag out in a wind with Blender's cloth solver and keep frames for picking one.

blender -b --factory-startup -t 2 --python sim_flag.py -- <work dir> [cells along the fly] [frames]
Simulated at real size in metres, saved in inches: x along the fly, y across the wind, z up, hoist at x = 0.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK = argv[0]
NX = int(argv[1]) if len(argv) > 1 else 64
FRAMES = int(argv[2]) if len(argv) > 2 else 96
os.makedirs(WORK, exist_ok=True)

IN = 0.0254
FLY, DROP = 40.0 * IN, 27.0 * IN
NZ = round(NX * DROP / FLY)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 24

xs = np.linspace(0, FLY, NX + 1)
zs = np.linspace(0, DROP, NZ + 1)
verts = [(x, 0.0, z) for z in zs for x in xs]
faces = []
for j in range(NZ):
    for i in range(NX):
        a = j * (NX + 1) + i
        faces.append((a, a + 1, a + NX + 2, a + NX + 1))
mesh = bpy.data.meshes.new("flag")
mesh.from_pydata(verts, [], faces)
for p in mesh.polygons:
    p.use_smooth = True
flag = bpy.data.objects.new("flag", mesh)
scene.collection.objects.link(flag)

pin = flag.vertex_groups.new(name="pin")
# The hoist is held by its heading strip, tight at both hooks and a little loose between them.
for j in range(NZ + 1):
    t = j / NZ
    pin.add([j * (NX + 1)], 1.0, "REPLACE")
    if 0 < j < NZ:
        verts_x = 0.5 * IN * math.sin(math.pi * t)
        mesh.vertices[j * (NX + 1)].co.x = verts_x

mod = flag.modifiers.new("cloth", "CLOTH")
s = mod.settings
s.quality = 10
s.mass = 0.12 * (64 / NX) ** 2
s.air_damping = 1.2
s.tension_stiffness = 22
s.compression_stiffness = 12
s.shear_stiffness = 6
s.bending_stiffness = 0.06
s.vertex_group_mass = "pin"
s.pin_stiffness = 5.0
mod.collision_settings.use_collision = False
cache = mod.point_cache
cache.frame_start, cache.frame_end = 1, FRAMES


def field(kind, at, aim, strength, flow, noise, size=1.0, seed=7):
    bpy.ops.object.effector_add(type=kind, location=at)
    empty = bpy.context.object
    empty.rotation_mode = "QUATERNION"
    empty.rotation_quaternion = Vector(aim).to_track_quat("Z", "Y")
    empty.field.strength = strength
    empty.field.flow = flow
    empty.field.noise = noise
    empty.field.seed = seed
    if kind == "TURBULENCE":
        empty.field.size = size
    return empty


# Blender's wind only pushes on a face's normal, and a flag lies along the wind, so the steady pull along the fly is
# drag written as gravity. The cross gusts make the folds.
scene.gravity = (17.0, 0.0, -6.5)
gust = field("WIND", (0.5, -1.0, DROP / 2), (0.0, 1.0, 0.0), 0.0, 0.0, 12.0)
field("TURBULENCE", (0.5, 0.0, DROP / 2), (0.0, 1.0, 0.0), 26.0, 0.5, 0.0, size=0.34, seed=31)
field("TURBULENCE", (0.3, 0.0, 0.1), (0.1, 1.0, 0.3), 12.0, 0.5, 0.0, size=0.13, seed=4)

count = len(mesh.vertices)
kept = {}
buffer = np.empty(count * 3, np.float32)
for frame in range(1, FRAMES + 1):
    gust.field.strength = 14.0 * math.sin(frame * 0.41) + 7.0 * math.sin(frame * 0.97 + 1.0)
    scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    evald = flag.evaluated_get(dg)
    em = evald.to_mesh()
    em.vertices.foreach_get("co", buffer)
    evald.to_mesh_clear()
    if frame >= 30 and frame % 3 == 0:
        kept[f"f{frame:03d}"] = buffer.reshape(-1, 3).copy() / IN
    if frame % 12 == 0:
        print("frame", frame, "extent x", round(float(buffer[0::3].max()) / IN, 1), "y", round(float(np.ptp(buffer[1::3])) / IN, 1), flush=True)

path = os.path.join(WORK, f"flag_sim_{NX}.npz")
np.savez_compressed(path, nx=NX, nz=NZ, **kept)
print("saved", path, flush=True)


# Rank the frames: the flag should fill its side view, not hang or sit edge-on.
def rank(p):
    grid = p.reshape(NZ + 1, NX + 1, 3)
    a = grid[:-1, :-1, [0, 2]]
    b = grid[:-1, 1:, [0, 2]]
    c = grid[1:, 1:, [0, 2]]
    d = grid[1:, :-1, [0, 2]]
    area = 0.5 * np.abs((c[..., 0] - a[..., 0]) * (d[..., 1] - b[..., 1]) - (d[..., 0] - b[..., 0]) * (c[..., 1] - a[..., 1]))
    return float(area.sum()) / (40.0 * 27.0), float(p[:, 0].max()), float(p[:, 2].min()), float(np.ptp(p[:, 1]))


scores = {k: rank(v) for k, v in kept.items()}
for k, v in scores.items():
    print(k, "fill %.2f reach %.1f low %.1f depth %.1f" % v)

# Look at a spread of frames.
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8
scene.cycles.use_denoising = False
scene.render.threads_mode = "FIXED"
scene.render.threads = 2
scene.render.resolution_x, scene.render.resolution_y = 560, 420
scene.frame_set(1)
flag.modifiers.remove(mod)
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = (math.radians(55), 0, math.radians(30))
w = bpy.data.worlds.new("w")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.55, 0.62, 1)
scene.world = w
m = bpy.data.materials.new("cloth")
m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.65, 0.09, 0.09, 1)
mesh.materials.append(m)
cam = bpy.data.cameras.new("c")
cam.lens = 55
co = bpy.data.objects.new("c", cam)
scene.collection.objects.link(co)
scene.camera = co
co.location = (0.55, -2.1, 0.45)
co.rotation_euler = (Vector((0.5, 0, DROP / 2)) - co.location).to_track_quat("-Z", "Y").to_euler()
names = sorted(kept)
for name in names[:: max(1, len(names) // 6)]:
    pts = (kept[name] * IN).astype(np.float32).ravel()
    mesh.vertices.foreach_set("co", pts)
    mesh.update()
    scene.render.filepath = os.path.join(WORK, f"flag_preview_{NX}_{name}.png")
    bpy.ops.render.render(write_still=True)
print("previews done", flush=True)
