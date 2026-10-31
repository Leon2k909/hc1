"""Matched Cycles renders of the churchyard: the old stones as the game draws them, then v2's in the same places. Not engine screenshots.

blender -b --factory-startup -t 4 --python render_headstone.py -- <project root> <export dir> <work dir> <out dir> <width> <samples> <views> [after]

Same camera, light, exposure and ACES 1.3 view for both, with back faces culled, as the engine does. The lawn, path, walls and ivy round them come from the map's own
west half, read through its vmdl; only the ground beyond that is a stand-in. Each new stone stands at its old stone's measured place and turn.
"""
import json
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, EXPORT, WORK, OUT = argv[0], argv[1], argv[2], argv[3]
WIDTH, SAMPLES = int(argv[4]), int(argv[5])
WANTED = argv[6].split(",")
ONLY = argv[7] if len(argv) > 7 else ""
os.makedirs(OUT, exist_ok=True)
ASSETS = os.path.join(ROOT, "Assets")
STONES = json.load(open(os.path.join(WORK, "old_stones.json")))
TOPS = {"low": 26.0, "shouldered": 29.0, "arched": 32.0}
REGION = ((-930.0, -400.0), (200.0, 660.0))

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
        b.inputs["Base Color"].default_value = (*[x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in srgb], 1)
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
    # The yard walls and the ivy use the map's own shaders, so they name their colour differently. Plain stand-ins for those here, from the same maps.
    surface = b.outputs[0]
    masonry = tex("TextureStoneColor", True)
    if masonry:
        scale = numbers(keys.get("g_vMasonryUvScale", "[1 1]"))
        coords = nt.nodes.new("ShaderNodeTexCoord")
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Scale"].default_value = (scale[0], scale[1], 1)
        nt.links.new(coords.outputs["UV"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs[0], masonry.inputs["Vector"])
        tint = nt.nodes.new("ShaderNodeRGB")
        tint.outputs[0].default_value = (*numbers(keys.get("g_vMasonryTint", "[1 1 1]"))[:3], 1)
        times = nt.nodes.new("ShaderNodeMixRGB")
        times.blend_type = "MULTIPLY"
        times.inputs[0].default_value = 1.0
        nt.links.new(masonry.outputs[0], times.inputs[1])
        nt.links.new(tint.outputs[0], times.inputs[2])
        nt.links.new(times.outputs[0], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.9
    plants = tex("TexturePlants", True)
    if plants:
        nt.links.new(plants.outputs[0], b.inputs["Base Color"])
        b.inputs["Roughness"].default_value = 0.7
        hole = nt.nodes.new("ShaderNodeBsdfTransparent")
        cut = nt.nodes.new("ShaderNodeMixShader")
        step = nt.nodes.new("ShaderNodeMath")
        step.operation = "GREATER_THAN"
        step.inputs[1].default_value = float(keys.get("g_flAlphaTestReference", 0.42))
        nt.links.new(plants.outputs[1], step.inputs[0])
        nt.links.new(step.outputs[0], cut.inputs[0])
        nt.links.new(hole.outputs[0], cut.inputs[1])
        nt.links.new(b.outputs[0], cut.inputs[2])
        surface = cut.outputs[0]
    out = nt.nodes["Material Output"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(surface, mix.inputs[1])
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


def make_object(name, mat, polys, positions, uvs, normals):
    vs, us, ns, idx = [], [], [], []
    for poly in polys:
        start = len(vs)
        for tok in poly:
            vs.append(positions[int(tok[0]) - 1])
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


text = open(os.path.join(ASSETS, "models/maps/belltower/belltower_west.vmdl"), encoding="utf-8").read()
remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', text))
files = [f for f in re.findall(r'filename = "([^"]+\.obj)"', text) if "hull" not in f]
stone_xy = np.array([(s["x"], s["y"]) for s in STONES])
mats = {}
old = []
kept = 0
for rel in files:
    path = os.path.join(ASSETS, rel)
    if not os.path.exists(path):
        continue
    positions, uvs, normals, faces = read_obj(path)
    if not positions:
        continue
    pts = np.array(positions)
    inside = (pts[:, 0] > REGION[0][0]) & (pts[:, 0] < REGION[0][1]) & (pts[:, 1] > REGION[1][0]) & (pts[:, 1] < REGION[1][1])
    for paint, polys in faces.items():
        near = [p for p in polys if inside[[int(t[0]) - 1 for t in p]].any()]
        if not near:
            continue
        if paint not in mats:
            mats[paint] = material(os.path.join(ASSETS, remaps[paint]), ASSETS)
        stones, rest, front = [], [], []
        for p in near:
            corners = pts[[int(t[0]) - 1 for t in p]]
            close = np.linalg.norm(corners[:, None, :2] - stone_xy[None], axis=2).min(1).max() < 13.5
            if paint == "ashlar_grey" and close and corners[:, 2].max() <= 40.1:
                stones.append(p)
            # The region's edge cuts what stands there into loose pieces. They still cast their shadows, but the far view looks past them.
            elif corners[:, 0].mean() > REGION[0][1] - 30.0:
                front.append(p)
            else:
                rest.append(p)
        if rest:
            make_object("map_" + paint, mats[paint], rest, positions, uvs, normals)
        if front:
            make_object("front_" + paint, mats[paint], front, positions, uvs, normals).visible_camera = False
        if stones:
            old.append(make_object("old_stones", mats[paint], stones, positions, uvs, normals))
        kept += len(near)
print("map faces", kept, "old stone objects", len(old), flush=True)

new = []
stone_mat = material(os.path.join(EXPORT, "materials/belltower/headstone_v2/headstone.vmat"), EXPORT)
meshes = {}
for s in STONES:
    if s["kind"] == "cross":
        kind = "cross"
    else:
        kind = min(TOPS, key=lambda k: abs(TOPS[k] - s["height"]))
    s["model"] = kind
    if kind not in meshes:
        positions, uvs, normals, faces = read_obj(os.path.join(EXPORT, "models/props/belltower/headstone_v2", f"headstone_{kind}_lod0.obj"))
        meshes[kind] = make_object(kind, stone_mat, next(iter(faces.values())), positions, uvs, normals)
        meshes[kind].hide_render = True
    ob = meshes[kind].copy()
    ob.hide_render = False
    ob.matrix_world = Matrix.Translation((s["x"], s["y"], 0.0)) @ Matrix.Rotation(math.radians(s["yaw"]), 4, "Z")
    scene.collection.objects.link(ob)
    new.append(ob)
print("new stones", {k: sum(s["model"] == k for s in STONES) for k in ("arched", "shouldered", "low", "cross")}, flush=True)

# The ground beyond the churchyard: a dull rough grass, the same for both.
floor = bpy.data.meshes.new("ground")
# Just under the map's lawn and gravel, as faces on one plane render black or not at all.
floor.from_pydata([(-2500, -1500, -0.5), (1500, -1500, -0.5), (1500, 2500, -0.5), (-2500, 2500, -0.5)], [], [(0, 1, 2, 3)])
g = bpy.data.materials.new("ground")
g.use_nodes = True
nt = g.node_tree
b = nt.nodes["Principled BSDF"]
tex = nt.nodes.new("ShaderNodeTexNoise")
tex.inputs["Scale"].default_value = 0.12
tex.inputs["Detail"].default_value = 10.0
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.35
ramp.color_ramp.elements[0].color = (0.05, 0.075, 0.025, 1)
ramp.color_ramp.elements[1].position = 0.7
ramp.color_ramp.elements[1].color = (0.14, 0.16, 0.06, 1)
nt.links.new(tex.outputs[0], ramp.inputs[0])
nt.links.new(ramp.outputs[0], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 0.95
floor.materials.append(g)
scene.collection.objects.link(bpy.data.objects.new("ground", floor))

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
# On the stones' inscribed faces, and low enough to rake across them.
so.rotation_euler = Vector((0.74, -0.42, 0.62)).to_track_quat("Z", "Y").to_euler()
cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 30000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co


def aim(eye, target, lens, aspect):
    co.location = eye
    co.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = int(WIDTH * aspect)


def northmost(kind):
    """The stone of a kind nearest the churchyard's north side, with nothing in front of its face."""
    return max((s for s in STONES if s["model"] == kind), key=lambda s: s["x"])


def in_front(s, dist, side, z):
    return (s["x"] + dist, s["y"] + side, z)


row = [s for s in STONES if s["y"] > 450]
mid_y = sum(s["y"] for s in row) / len(row)
a, sh, lo, cr = northmost("arched"), northmost("shouldered"), northmost("low"), northmost("cross")
# name: eye, target, lens, aspect. A standing player's eye is 64 in up.
VIEWS = {
    "yard": ((-436.0, mid_y + 64.0, 64.0), (-560.0, mid_y - 10.0, 14.0), 26, 0.66),
    "far": ((-30.0, mid_y + 14.0, 64.0), (-500.0, mid_y, 18.0), 44, 0.5),
    "arched": (in_front(a, 44.0, -14.0, 40.0), (a["x"], a["y"], 16.0), 34, 0.74),
    "shouldered": (in_front(sh, 40.0, 16.0, 34.0), (sh["x"], sh["y"], 14.0), 34, 0.74),
    "low": (in_front(lo, 38.0, -14.0, 30.0), (lo["x"], lo["y"], 12.0), 34, 0.74),
    "cross": (in_front(cr, 54.0, 20.0, 46.0), (cr["x"], cr["y"], 20.0), 34, 0.74),
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
