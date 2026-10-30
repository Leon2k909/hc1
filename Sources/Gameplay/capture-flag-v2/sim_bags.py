"""Drop filled sandbags onto a foot plate with Blender's cloth solver, one pile at a time.

blender -b --factory-startup -t 2 --python sim_bags.py -- <work dir> [cells along a bag] [only this pile]
Pile frame, inches: x outward from the mast, z up, foot plate from x -5.5..5.5, y -5..5, top at 0.45.
Each bag is one closed sheet: a top grid and a bottom grid that share their edge, so the seam is real.
"""
import math
import os
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK = argv[0]
NX = int(argv[1]) if len(argv) > 1 else 72
ONLY = int(argv[2]) if len(argv) > 2 else None
os.makedirs(WORK, exist_ok=True)

IN = 0.0254
LENGTH, WIDTH, THICK = 19.0, 11.0, 5.8
NY = round(NX * WIDTH / LENGTH)
FRAMES = 42

# Pile, bag: centre x, y, height it starts at, yaw in degrees, seed.
PILES = [
    [(3.6, 0.2, 3.9, 87, 11), (3.8, -0.4, 9.4, 96, 12), (3.2, 0.6, 14.8, 82, 13)],
    [(3.5, -0.3, 3.9, 93, 21), (3.9, 0.8, 9.4, 80, 22)],
    [(3.7, 0.5, 3.9, 84, 31), (3.2, -0.5, 9.4, 99, 32)],
]


def topology(nx, ny):
    """Index of every top and bottom grid point; the bottom's edge is the top's edge."""
    top = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
    bottom = np.full_like(top, -1)
    bottom[0, :] = top[0, :]
    bottom[-1, :] = top[-1, :]
    bottom[:, 0] = top[:, 0]
    bottom[:, -1] = top[:, -1]
    inner = (nx - 1) * (ny - 1)
    bottom[1:-1, 1:-1] = top.size + np.arange(inner).reshape(ny - 1, nx - 1)
    return top, bottom, top.size + inner


def bag_mesh(name, seed):
    top, bottom, count = topology(NX, NY)
    rng = np.random.default_rng(seed)
    gx = np.linspace(-1, 1, NX + 1)
    gy = np.linspace(-1, 1, NY + 1)
    X, Y = np.meshgrid(gx, gy)
    # Starts as a full pillow, narrower than its flat size so the sheet has somewhere to wrinkle to.
    rim = np.clip(1 - np.abs(X) ** 5, 0, 1) ** 0.5 * np.clip(1 - np.abs(Y) ** 4, 0, 1) ** 0.5
    lump = np.random.default_rng(seed + 100).standard_normal(X.shape)
    pts = np.zeros((count, 3))
    for grid, sign in ((top, 1), (bottom, -1)):
        ok = grid >= 0
        pts[grid[ok], 0] = (X[ok] * LENGTH * 0.5)
        pts[grid[ok], 1] = (Y[ok] * WIDTH * 0.5)
        pts[grid[ok], 2] = sign * (THICK * 0.5) * rim[ok]
    pts += rng.normal(0, 0.012, pts.shape)
    faces = []
    for j in range(NY):
        for i in range(NX):
            faces.append((top[j, i], top[j, i + 1], top[j + 1, i + 1], top[j + 1, i]))
            faces.append((bottom[j, i], bottom[j + 1, i], bottom[j + 1, i + 1], bottom[j, i + 1]))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata((pts * IN).tolist(), [], faces)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return mesh


def collider(ob):
    bpy.context.view_layer.objects.active = ob
    ob.modifiers.new("collision", "COLLISION")
    ob.collision.thickness_outer = 0.0015
    ob.collision.cloth_friction = 40.0
    ob.collision.damping = 0.9


def settle(ob, frames):
    mod = ob.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    s.quality = 7
    # About 15 kg of sand, held out by the volume it fills and pooling under its own weight.
    s.mass = 0.012 * (72 / NX) ** 2
    s.air_damping = 5.0
    s.tension_stiffness = 42
    s.compression_stiffness = 18
    s.shear_stiffness = 14
    s.bending_stiffness = 0.8
    s.use_pressure = True
    s.use_pressure_volume = False
    s.target_volume = LENGTH * WIDTH * THICK * 0.86 * IN**3
    s.pressure_factor = 7.0
    s.uniform_pressure_force = 0.0
    s.fluid_density = 0.9
    c = mod.collision_settings
    c.use_collision = True
    c.collision_quality = 3
    c.distance_min = 0.0022
    c.friction = 30.0
    c.use_self_collision = False
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, frames
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, frames
    count = len(ob.data.vertices)
    buf = np.empty(count * 3, np.float32)
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    em = e.to_mesh()
    world = np.array(e.matrix_world, dtype=np.float64)
    em.vertices.foreach_get("co", buf)
    e.to_mesh_clear()
    pts = buf.reshape(-1, 3).astype(np.float64)
    pts = pts @ world[:3, :3].T + world[:3, 3]
    ob.modifiers.remove(mod)
    ob.data.vertices.foreach_set("co", pts.astype(np.float32).ravel())
    ob.matrix_world.identity()
    ob.data.update()
    return pts / IN


for index, pile in enumerate(PILES):
    if ONLY is not None and index != ONLY:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0, 0, 0))
    collider(bpy.context.object)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0.225 * IN))
    plate = bpy.context.object
    plate.scale = (11 * IN, 10 * IN, 0.45 * IN)
    bpy.ops.object.transform_apply(scale=True)
    collider(plate)
    result = {}
    for k, (cx, cy, cz, yaw, seed) in enumerate(pile):
        mesh = bag_mesh(f"bag{index}_{k}", seed)
        ob = bpy.data.objects.new(mesh.name, mesh)
        scene.collection.objects.link(ob)
        ob.location = (cx * IN, cy * IN, cz * IN)
        ob.rotation_euler = (math.radians(1.5 * (k - 1)), math.radians(-1.0 * k), math.radians(yaw))
        bpy.context.view_layer.update()
        result[f"bag{k}"] = settle(ob, FRAMES)
        collider(ob)
        print(f"pile {index} bag {k}: z {result[f'bag{k}'][:, 2].min():.2f}..{result[f'bag{k}'][:, 2].max():.2f}", flush=True)
    np.savez_compressed(os.path.join(WORK, f"pile_{index}_{NX}.npz"), nx=NX, ny=NY, **result)

    # One look at the pile.
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = 640, 440
    m = bpy.data.materials.new("hessian")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.32, 0.26, 0.17, 1)
    for ob in scene.objects:
        if ob.type == "MESH":
            ob.data.materials.append(m)
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.5
    so = bpy.data.objects.new("sun", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), 0, math.radians(35))
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.6, 0.68, 1)
    scene.world = w
    cam = bpy.data.cameras.new("c")
    cam.lens = 45
    co = bpy.data.objects.new("c", cam)
    scene.collection.objects.link(co)
    scene.camera = co
    from mathutils import Vector

    target = Vector((3 * IN, 0, 4 * IN))
    co.location = target + Vector((30 * IN, -30 * IN, 18 * IN))
    co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(WORK, f"pile_{index}_{NX}.png")
    bpy.ops.render.render(write_still=True)
print("bags done", flush=True)
