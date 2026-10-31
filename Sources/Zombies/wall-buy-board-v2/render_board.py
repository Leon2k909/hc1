"""Matched Cycles renders of the old wall-buy board and v2's exported files. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_board.py -- <project root> <out dir> <width> <samples> <views> [lod]

The station is built as CreateStation builds it: the old board is the dev box (primary_white under its brown tint), the gun
is the AK-105's world model with its default parts, scaled and centred by the same sums, and the station's warm light
stands where the code puts it. Everything is in station space, so the floor is z 0, and the new model sits at the old
board's position, (-4, 0, 40).
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
LOD = int(argv[5]) if len(argv) > 5 else 0
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
scene.view_settings.exposure = -0.2


def vmat_keys(rel):
    keys = {}
    for line in open(os.path.join(ASSETS, rel), encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def material(rel):
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

    got = tex("TextureColor", True)
    if got:
        nt.links.new(got.outputs[0], b.inputs["Base Color"])
    got = tex("TextureRoughness", False)
    if got:
        nt.links.new(got.outputs[0], b.inputs["Roughness"])
    got = tex("TextureMetalness", False)
    if got:
        nt.links.new(got.outputs[0], b.inputs["Metallic"])
    got = tex("TextureNormal", False)
    if got:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(got.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return mat


def make_mesh(name, vs, us, ns, idx, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vs, [], idx)
    layer = mesh.uv_layers.new(name="UVMap")
    corner = np.array([us[v] for poly in idx for v in poly], np.float32)
    layer.data.foreach_set("uv", corner.ravel())
    if ns is not None:
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set_from_vertices(ns)
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    return ob


def load_obj(path, mat, at):
    positions, uvs, normals = [], [], []
    vs, us, ns, idx = [], [], [], []
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
            start = len(vs)
            for tok in line.split()[1:]:
                p, t, n = tok.split("/")
                vs.append(positions[int(p) - 1])
                us.append(uvs[int(t) - 1])
                ns.append(normals[int(n) - 1])
            idx.append(tuple(range(start, start + 3)))
    ob = make_mesh(os.path.basename(path), vs, us, ns, idx, mat)
    ob.location = at
    return ob


def floats(text, key, kind):
    m = re.search(r'"%s" "%s"\s*\[(.*?)\]' % (re.escape(key), kind), text, re.S)
    return np.array(" ".join(re.findall(r'"([^"]+)"', m.group(1))).split(), float)


def read_dmx(path):
    """A keyvalues2 DMX's corners in engine axes: per material, (positions, uvs, normals, polygons)."""
    text = open(path, encoding="utf-8", errors="ignore").read()
    p = floats(text, "position$0", "vector3_array").reshape(-1, 3)
    pi = floats(text, "position$0Indices", "int_array").astype(int)
    t = floats(text, "texcoord$0", "vector2_array").reshape(-1, 2)
    ti = floats(text, "texcoord$0Indices", "int_array").astype(int)
    n = floats(text, "normal$0", "vector3_array").reshape(-1, 3)
    ni = floats(text, "normal$0Indices", "int_array").astype(int)
    names = {}
    for m in re.finditer(r'"mtlName" "string" "([^"]+)"', text):
        at = text.rfind('"elementid" "', 0, m.start()) + len('"elementid" "')
        names[text[at : text.index('"', at)]] = m.group(1)
    out = {}
    for m in re.finditer(r'"material" "element" "([^"]+)"\s*"faces" "int_array"\s*\[(.*?)\]', text, re.S):
        stream = np.array(re.findall(r'"(-?\d+)"', m.group(2)), int)
        polys, cur = [], []
        for v in stream:
            if v < 0:
                polys.append(cur)
                cur = []
            else:
                cur.append(v)
        out.setdefault(names[m.group(1)], []).extend(polys)
    return p[pi], t[ti], n[ni], out


def load_gun():
    root = os.path.join(ASSETS, "Weapons/AK105")
    vmdl = open(os.path.join(root, "w_ak105.vmdl"), encoding="utf-8").read()
    remap = dict(re.findall(r'from = "([^"]+)\.vmat"\s*to = "([^"]+)"', vmdl))
    names = ["w_ak105", "w_ak105_muzzle_tip", "w_ak105_stock_hinge", "w_ak105_stock_ar_akilo105_stock_v0", "w_ak105_pistol_grip_ar_akilo105_pgrip_v0", "w_ak105_magazine_ar_akilo105_mag_v0"]
    parts = [read_dmx(os.path.join(root, "models", n + ".dmx")) for n in names if os.path.exists(os.path.join(root, "models", n + ".dmx"))]
    allp = np.concatenate([p[np.unique(np.concatenate([np.array(q) for f in faces.values() for q in f]))] for p, _, _, faces in parts])
    lo, hi = allp.min(0), allp.max(0)
    centre, size = (lo + hi) / 2, hi - lo
    scale = min(1.4, 50.0 / max(size[0], 1.0))
    print("gun bounds", lo.round(2), hi.round(2), "scale %.3f" % scale, flush=True)

    def place(v):
        q = (v - centre) * scale
        return np.column_stack((2.0 - q[:, 1], q[:, 0], 40.0 + q[:, 2]))

    def turn(v):
        return np.column_stack((-v[:, 1], v[:, 0], v[:, 2]))

    obs = []
    placed_x = []
    for p, t, n, faces in parts:
        world = place(p)
        nor = turn(n)
        for mname, polys in faces.items():
            used = np.unique(np.concatenate([np.array(q) for q in polys]))
            placed_x.append(world[used, 0])
            lookup = -np.ones(len(p), int)
            lookup[used] = np.arange(len(used))
            idx = [tuple(lookup[q]) for q in polys]
            uv = t[used]
            mat = material(remap[mname]) if mname in remap else bpy.data.materials.new(mname)
            obs.append(make_mesh(mname, world[used].tolist(), uv.tolist(), nor[used].tolist(), idx, mat))
    print("gun back x %.2f front x %.2f" % (min(a.min() for a in placed_x), max(a.max() for a in placed_x)), flush=True)
    return obs


def block(name, lo, hi, colour, rough=0.85):
    mesh = bpy.data.meshes.new(name)
    x0, a0, b0 = lo
    x1, a1, b1 = hi
    v = [(x0, a0, b0), (x1, a0, b0), (x1, a1, b0), (x0, a1, b0), (x0, a0, b1), (x1, a0, b1), (x1, a1, b1), (x0, a1, b1)]
    mesh.from_pydata(v, [], [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*colour, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = rough
    mesh.materials.append(m)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    return ob


# The old board: Color( 0.28, 0.2, 0.13 ) over a plain white material.
old = [block("old board", (-5, -30, 20), (-3, 30, 60), (0.28, 0.2, 0.13), 0.6)]
new_dir = os.path.join(ASSETS, "models/zombies/wall_buy_board_v2")
new_mat = material("materials/zombies/wall_buy_board_v2/wall_buy_board.vmat")
new = [load_obj(os.path.join(new_dir, f"wall_buy_board_lod{LOD}.obj"), new_mat, (-4, 0, 40))]
load_gun()

# The same plain wall and floor for both: the station stands an inch off the wall when there's one close.
wall = block("wall", (-14, -240, 0), (-6, 240, 150), (0.2, 0.19, 0.17))
block("floor", (-400, -400, -2), (400, 400, 0), (0.17, 0.16, 0.14), 0.8)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(bpy.utils.resource_path("LOCAL"), "datafiles", "studiolights", "world", "courtyard.exr"))
coord = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(40))
nt.links.new(coord.outputs["Generated"], mapping.inputs[0])
nt.links.new(mapping.outputs[0], env.inputs[0])
nt.links.new(env.outputs[0], bg.inputs[0])
bg.inputs[1].default_value = 0.7
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 2.6
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((1.0, -0.72, 1.05)).to_track_quat("Z", "Y").to_euler()
# The station's own light, where CreateStation puts it, in its colour.
lamp = bpy.data.lights.new("station light", "POINT")
lamp.energy = 16000
lamp.color = (1.0, 0.85, 0.6)
lo = bpy.data.objects.new("station light", lamp)
scene.collection.objects.link(lo)
lo.location = (30, 0, 48)

cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
# name: eye, target, lens, aspect, wall behind.
VIEWS = {
    "whole": ((118, -74, 58), (0, 0, 31), 40, 0.9, True),
    "near": ((38, -18, 62), (-2, 2, 40), 24, 0.75, True),
    "low": ((36, -46, 14), (0, -24, 10), 30, 0.75, True),
    "lock": ((17, 13, 37), (-2, 24, 30), 40, 0.85, True),
    "rear": ((-86, -52, 46), (0, 0, 30), 40, 0.85, False),
    "far": ((300, -160, 64), (0, 0, 30), 60, 0.9, True),
}
for name in WANTED:
    eye, target, lens, aspect, walled = VIEWS[name]
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    wall.hide_render = not walled
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)
    for variant, shown, hidden in (("before", old, new), ("after", new, old)):
        for ob in shown:
            ob.hide_render = False
        for ob in hidden:
            ob.hide_render = True
        tail = f"-lod{LOD}" if LOD else ""
        scene.render.filepath = os.path.join(OUT, f"{name}-{variant}{tail}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, variant, flush=True)
print("renders done", flush=True)
