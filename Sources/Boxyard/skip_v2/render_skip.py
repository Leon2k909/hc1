"""Matched Cycles renders of Boxyard's shipped skip and v2's exported files, on one concrete yard. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_skip.py -- <project root> <export dir> <out dir> <width> <samples> <views> [lods|after]

Same camera, light, exposure and ACES 1.3 view for both. Back faces are culled for both, as the engine does: the old skip's
walls have a face on each side in one plane, which Cycles can't tell apart (they came out black, or missing), so each old
face is moved 0.03 in along its own normal for the render. The old skip is cut out of Boxyard's merged props by its material
and position, and moved into this model's frame.
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


def material(vmat_path, root):
    """Maps where the vmat has them, values where it doesn't, and back faces culled."""
    keys = vmat_keys(vmat_path)
    mat = bpy.data.materials.new(os.path.basename(vmat_path))
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]

    def tex(key, colour):
        path = keys.get(key)
        if not path or not os.path.exists(os.path.join(root, path)):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(root, path), check_existing=True)
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


def make_object(name, mat, polys, positions, uvs, normals, place, nudge=0.0):
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        start = len(vs)
        corners = [np.array(place(positions[int(tok[0]) - 1])) for tok in poly]
        out = np.cross(corners[1] - corners[0], corners[-1] - corners[0])
        out = out / max(np.linalg.norm(out), 1e-9) * nudge
        for tok, corner in zip(poly, corners):
            vs.append(tuple(corner + out))
            us.append(uvs[int(tok[1]) - 1] if len(tok) > 1 and tok[1] else (0, 0))
            if len(tok) > 2 and tok[2]:
                ns.append(place(normals[int(tok[2]) - 1], True))
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


def load_new(lod=0, shift=(0, 0, 0)):
    path = os.path.join(EXPORT, "models/props/boxyard/skip_v2", f"skip_lod{lod}.obj")
    positions, uvs, normals, faces = read_obj(path)
    mat = material(os.path.join(EXPORT, "materials/boxyard/skip_v2/skip.vmat"), EXPORT)

    def place(p, is_normal=False):
        return p if is_normal else (p[0] + shift[0], p[1] + shift[1], p[2] + shift[2])

    return [make_object(f"new{lod}", mat, polys, positions, uvs, normals, place) for polys in faces.values()]


def load_old():
    """Boxyard's skip: engine (X, Y) = (675 + local y, 555 - local x), so local x = 555 - Y and local y = X - 675."""
    positions, uvs, normals, faces = read_obj(os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.obj"))
    remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', open(os.path.join(ASSETS, "models/maps/boxyard/boxyard_props.vmdl"), encoding="utf-8").read()))

    def place(p, is_normal=False):
        if is_normal:
            return (-p[1], p[0], p[2])
        return (555.0 - p[1], p[0] - 675.0, p[2])

    def in_skip(poly):
        for tok in poly:
            x, y, z = positions[int(tok[0]) - 1]
            if not (630 < x < 720 and 475 < y < 635 and z < 49):
                return False
        return True

    obs = []
    for name, polys in faces.items():
        kept = [poly for poly in polys if in_skip(poly)]
        if kept:
            print("old", name, len(kept), flush=True)
            obs.append(make_object("old_" + name, material(os.path.join(ASSETS, remaps[name]), ASSETS), kept, positions, uvs, normals, place, 0.03))
    return obs


# A plain concrete yard and a wall behind it: the same for both.
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
    tex.inputs["Scale"].default_value = 0.05
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
    scene.collection.objects.link(bpy.data.objects.new(name, mesh))


slab("yard", (-1400, -1400, -4), (1400, 1400, 0), (0.26, 0.25, 0.23), 0.9)
slab("wall", (-1400, 210, 0), (1400, 226, 500), (0.36, 0.34, 0.31), 0.9)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
bg.inputs[0].default_value = (0.62, 0.72, 0.92, 1)
bg.inputs[1].default_value = 1.1
scene.world = world
sun = bpy.data.lights.new("sun", "SUN")
sun.energy = 3.6
sun.angle = math.radians(1.6)
sun.color = (1.0, 0.95, 0.88)
so = bpy.data.objects.new("sun", sun)
scene.collection.objects.link(so)
so.rotation_euler = Vector((0.32, -0.42, 0.86)).to_track_quat("Z", "Y").to_euler()
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


if LODS:
    obs = []
    for lod in range(4):
        obs += load_new(lod, ((lod - 1.5) * 185, 0, 0))
    aim((0, -190, 560), (0, 0, 8), 40, 0.42)
    scene.render.filepath = os.path.join(OUT, "lods.png")
    bpy.ops.render.render(write_still=True)
    print("rendered lods", flush=True)
    print("renders done", flush=True)
    sys.exit(0)

old = load_old()
new = load_new()
# name: eye, target, lens, aspect. A standing player's eye is 64 in up.
VIEWS = {
    "player": ((120, -150, 64), (0, 0, 22), 34, 0.66),
    "above": ((-110, -120, 122), (-4, 0, 16), 34, 0.66),
    "end": ((165, 42, 58), (64, 0, 24), 36, 0.66),
    "side": ((10, -150, 40), (10, -30, 26), 36, 0.66),
    "lug": ((88, -72, 50), (56, -34, 38), 36, 0.66),
    "inside": ((-74, 22, 118), (14, 0, 10), 34, 0.66),
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
