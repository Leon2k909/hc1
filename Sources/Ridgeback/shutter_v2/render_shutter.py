"""Matched Cycles renders of the town house's shutters and v2's exported files, either side of one test window. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_shutter.py -- <project root> <export dir> <out dir> <width> <samples> <views> [after]

Same camera, light, exposure and ACES 1.3 view for both, with back faces culled, as the engine does. The old pair is cut out of the town
house's model by its material and moved into this scene: wall face at x = 0, window centred on y = 0. The wall and window are stand-ins.
"""
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, EXPORT, OUT = argv[0], argv[1], argv[2]
WIDTH, SAMPLES = int(argv[3]), int(argv[4])
WANTED = argv[5].split(",")
ONLY = argv[6] if len(argv) > 6 else ""
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
WINDOW_HALF = 22.0  # The gap between the leaves: a window and its surrounds.
LEAF = 25.0

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
scene.render.image_settings.color_mode = "RGB"
scene.view_settings.view_transform = "ACES 1.3"
scene.view_settings.exposure = -0.3


def vmat_keys(path):
    keys = {}
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def numbers(text):
    return [float(x) for x in text.strip("[] ").split()]


def material(vmat_path, root):
    keys = vmat_keys(vmat_path)
    mat = bpy.data.materials.new(os.path.basename(vmat_path))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(key, colour):
        path = keys.get(key, "")
        if path.startswith("[") or not path or not os.path.exists(os.path.join(root, path)):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(root, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    c = tex("TextureColor", True)
    if c:
        nt.links.new(c.outputs[0], b.inputs["Base Color"])
    elif "g_vColorTint" in keys:
        srgb = numbers(keys["g_vColorTint"])[:3]
        linear = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in srgb]
        b.inputs["Base Color"].default_value = (*linear, 1)
    r = tex("TextureRoughness", False)
    if r:
        nt.links.new(r.outputs[0], b.inputs["Roughness"])
    elif keys.get("TextureRoughness", "").startswith("["):
        b.inputs["Roughness"].default_value = numbers(keys["TextureRoughness"])[0]
    m = tex("TextureMetalness", False)
    if m:
        nt.links.new(m.outputs[0], b.inputs["Metallic"])
    n = tex("TextureNormal", False)
    if n:
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(n.outputs[0], nm.inputs["Color"])
        nt.links.new(nm.outputs[0], b.inputs["Normal"])
    out = nt.nodes["Material Output"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(clear.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def read_obj(path):
    positions, uvs, normals = [], [], []
    faces = {}
    current = None
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
        elif line.startswith("usemtl"):
            current = line.split()[1]
            faces.setdefault(current, [])
        elif tag == "f ":
            faces[current].append([tok.split("/") for tok in line.split()[1:]])
    return positions, uvs, normals, faces


def make_object(name, mat, polys, positions, uvs, normals, shift=(0, 0, 0)):
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        start = len(vs)
        for tok in poly:
            p = positions[int(tok[0]) - 1]
            vs.append((p[0] + shift[0], p[1] + shift[1], p[2] + shift[2]))
            us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
            if len(tok) > 2 and tok[2]:
                ns.append(normals[int(tok[2]) - 1])
        idx.append(tuple(range(start, start + len(poly))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vs, [], idx)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
    if len(ns) == len(vs):
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    return ob


def load_new():
    mat = material(os.path.join(EXPORT, "materials/ridgeback/shutter_v2/shutter.vmat"), EXPORT)
    obs = []
    # The leaf at -y is hinged towards the window, at its +y side: shutter_l. The one at +y is shutter_r.
    for side, y in (("l", -(WINDOW_HALF + LEAF / 2)), ("r", WINDOW_HALF + LEAF / 2)):
        positions, uvs, normals, faces = read_obj(os.path.join(EXPORT, "models/props/ridgeback/shutter_v2", f"shutter_{side}_lod0.obj"))
        for polys in faces.values():
            obs.append(make_object(f"new_{side}", mat, polys, positions, uvs, normals, (0, y, 0)))
    return obs


def load_old():
    positions, uvs, normals, faces = read_obj(os.path.join(ASSETS, "models/buildings/town_house/town_house.obj"))
    remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', open(os.path.join(ASSETS, "models/buildings/town_house/town_house.vmdl"), encoding="utf-8").read()))
    polys = faces["shutter_green"]
    # Whichever leaves stand on the +X wall: take its two lowest, nearest each other, as they hang either side of one window.
    leaves = []
    for k in range(0, len(polys), 12):
        group = polys[k : k + 12]
        pts = np.array([positions[int(t[0]) - 1] for p in group for t in p])
        leaves.append((group, pts.min(0), pts.max(0)))
    wall = [l for l in leaves if l[2][0] > 100 and (l[2][0] - l[1][0]) < 2]
    z = min(l[1][2] for l in wall)
    row = sorted((l for l in wall if abs(l[1][2] - z) < 1), key=lambda l: l[1][1])
    best = min(range(len(row) - 1), key=lambda i: row[i + 1][1][1] - row[i][2][1])
    a, b = row[best], row[best + 1]
    print("old pair", a[1].round(1), a[2].round(1), b[1].round(1), b[2].round(1), flush=True)
    mat = material(os.path.join(ASSETS, remaps["shutter_green"]), ASSETS)
    # Each leaf moves on its own so the old pair sit exactly where the new pair do, on the same wall and floor.
    obs = []
    for leaf, y in ((a, -(WINDOW_HALF + LEAF / 2)), (b, WINDOW_HALF + LEAF / 2)):
        centre = (leaf[1] + leaf[2]) / 2
        obs.append(make_object("old", mat, leaf[0], positions, uvs, normals, (-leaf[1][0], y - centre[1], -leaf[1][2])))
    return obs


def slab(name, lo, hi, colour, rough=0.85, noisy=False):
    mesh = bpy.data.meshes.new(name)
    x0, a0, b0 = lo
    x1, a1, b1 = hi
    v = [(x0, a0, b0), (x1, a0, b0), (x1, a1, b0), (x0, a1, b0), (x0, a0, b1), (x1, a0, b1), (x1, a1, b1), (x0, a1, b1)]
    mesh.from_pydata(v, [], [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*colour, 1)
    b.inputs["Roughness"].default_value = rough
    mesh.materials.append(m)
    scene.collection.objects.link(bpy.data.objects.new(name, mesh))


# A plain rendered wall with a dark window between the leaves. Stand-ins for the town house's own, the same for both.
side_w = WINDOW_HALF
slab("wall", (-12, -400, -40), (0, 400, 200), (0.6, 0.55, 0.45), 0.9)
slab("window", (0, -side_w + 3.0, 2.0), (0.4, side_w - 3.0, 62.0), (0.02, 0.025, 0.03), 0.2)
slab("surround", (0, -side_w, -2.0), (1.2, side_w, 2.0), (0.62, 0.6, 0.55), 0.7)
slab("surround", (0, -side_w, 62.0), (1.2, side_w, 66.0), (0.62, 0.6, 0.55), 0.7)
slab("surround", (0, -side_w, 2.0), (1.2, -side_w + 3.0, 62.0), (0.62, 0.6, 0.55), 0.7)
slab("surround", (0, side_w - 3.0, 2.0), (1.2, side_w, 62.0), (0.62, 0.6, 0.55), 0.7)
world = bpy.data.worlds.new("sky")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.62, 0.72, 0.92, 1)
bg.inputs[1].default_value = 1.0
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.4
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
# Raking down across the face, which is what shows a surface up or lets it down.
so.rotation_euler = Vector((0.5, -0.5, 0.72)).to_track_quat("Z", "Y").to_euler()
cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 20000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co


def aim(eye, target, lens, aspect):
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)


old = load_old()
new = load_new()
leaf_y = WINDOW_HALF + LEAF / 2
# name: eye, target, lens, aspect. The town house's lower leaves start 32 in up, so a player looks at them straight on.
VIEWS = {
    "pair": ((150, -44, 40), (0, 0, 32), 34, 0.72),
    "leaf": ((64, -leaf_y - 34, 48), (1, -leaf_y, 34), 34, 0.8),
    "hinge": ((26, leaf_y - 24, 58), (1, leaf_y - 8, 52), 34, 0.72),
    "foot": ((26, -leaf_y - 30, 14), (1, -leaf_y - 8, 9), 34, 0.72),
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
