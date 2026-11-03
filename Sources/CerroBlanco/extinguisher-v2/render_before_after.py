"""Cerro Blanco's extinguishers before and after, from the map's own files: blender -b --factory-startup -t 4 --python render_before_after.py -- <project root> <out dir> <before|after>

Blender renders, not s&box: for when the editor's closed. "before" reads the fit-out from before-install, "after" reads it as it is now and stands the new model at each placement. Same camera for
both. Ceilings are left out so daylight gets in, and back faces are culled as the engine does. Faces wound against their own normal are turned round for the picture only, or the old bodies draw black.
"""
import json
import math
import os
import re
import sys

import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
ROOT, OUT, MODE = argv[0], argv[1], argv[2]
A = os.path.join(ROOT, "Assets")
WORK = os.path.join(ROOT, "output/asset-improvement-20261030/cerroblanco-extinguisher")
places = [p for p in json.load(open(os.path.join(WORK, "placements.json"))) if p["old_axis"][2] < 100]
os.makedirs(OUT, exist_ok=True)
MODELS = ["models/maps/cerroblanco/cerroblanco_buildings.vmdl", "models/maps/cerroblanco/cerroblanco_fitout.vmdl", "models/maps/cerroblanco/cerroblanco_fitout_fine.vmdl",
          "models/maps/cerroblanco/quality-v1/cerroblanco_detail_interior.vmdl", "models/maps/cerroblanco/quality-v1/cerroblanco_dressing_v2.vmdl"]
RADIUS, Z0, Z1 = 330.0, -6.0, 165.0
spots = np.array([p["old_axis"][:2] for p in places])

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 64
scene.cycles.use_adaptive_sampling = True
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "ACES 1.3"
scene.view_settings.exposure = -0.2


def keys_of(path):
    keys = {}
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*"?(\w+)"?\s+"?([^"\n]+?)"?\s*$', line)
        if m:
            keys[m.group(1)] = m.group(2).strip()
    return keys


def numbers(text):
    return [float(x) for x in text.strip("[] ").split()]


made = {}


def material(paint, vmat):
    if paint in made:
        return made[paint]
    mat = bpy.data.materials.new(paint)
    mat.use_nodes = True
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    keys = keys_of(os.path.join(A, vmat)) if vmat and os.path.exists(os.path.join(A, vmat)) else {}

    def tex(key, colour):
        path = keys.get(key, "")
        if not path or path.startswith("[") or not os.path.exists(os.path.join(A, path)):
            return None
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(os.path.join(A, path), check_existing=True)
        n.image.colorspace_settings.name = "sRGB" if colour else "Non-Color"
        return n

    tint = numbers(keys["g_vColorTint"])[:3] if keys.get("g_vColorTint", "").startswith("[") else [1.0, 1.0, 1.0]
    tint = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in tint]
    c = tex("TextureColor", True)
    if c:
        times = nt.nodes.new("ShaderNodeMixRGB")
        times.blend_type = "MULTIPLY"
        times.inputs[0].default_value = 1.0
        times.inputs[2].default_value = (*tint, 1)
        nt.links.new(c.outputs[0], times.inputs[1])
        nt.links.new(times.outputs[0], b.inputs["Base Color"])
    elif keys.get("TextureColor", "").startswith("["):
        b.inputs["Base Color"].default_value = (*numbers(keys["TextureColor"])[:3], 1)
    else:
        b.inputs["Base Color"].default_value = (*tint, 1)
    r = tex("TextureRoughness", False)
    if r:
        nt.links.new(r.outputs[0], b.inputs["Roughness"])
    elif keys.get("TextureRoughness", "").startswith("["):
        b.inputs["Roughness"].default_value = numbers(keys["TextureRoughness"])[0]
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
    made[paint] = mat
    return mat


def read_obj(path):
    positions, uvs, normals, paint, faces = [], [], [], None, {}
    for line in open(path, encoding="utf-8"):
        tag = line[:2]
        if tag == "v ":
            a, b, c = map(float, line[2:].split()[:3])
            positions.append((c, a, b))
        elif tag == "vt":
            uvs.append(tuple(map(float, line[3:].split()[:2])))
        elif tag == "vn":
            a, b, c = map(float, line[3:].split()[:3])
            normals.append((c, a, b))
        elif line.startswith("usemtl"):
            paint = line.split()[1]
            faces.setdefault(paint, [])
        elif tag == "f ":
            faces[paint].append([t.split("/") for t in line.split()[1:]])
    return positions, uvs, normals, faces


def make(paint, vmat, polys, positions, uvs, normals, transforms=((0.0, (0.0, 0.0, 0.0)),)):
    vs, us, ns, idx = [], [], [], []
    pts = np.array(positions)
    for yaw, at in transforms:
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        for poly in polys:
            q = pts[[int(t[0]) - 1 for t in poly[:3]]]
            # Turned round for this picture only when wound against its own normal.
            if len(poly[0]) > 2 and poly[0][2] and np.cross(q[1] - q[0], q[2] - q[0]) @ np.mean([normals[int(t[2]) - 1] for t in poly[:3]], axis=0) < 0:
                poly = poly[::-1]
            start = len(vs)
            for t in poly:
                x, y, z = positions[int(t[0]) - 1]
                vs.append((x * c - y * s + at[0], x * s + y * c + at[1], z + at[2]))
                us.append(uvs[int(t[1]) - 1] if len(t) > 1 and t[1] else (0, 0))
                if len(t) > 2 and t[2]:
                    nx, ny, nz = normals[int(t[2]) - 1]
                    ns.append((nx * c - ny * s, nx * s + ny * c, nz))
            idx.append(tuple(range(start, start + len(poly))))
    mesh = bpy.data.meshes.new(paint)
    mesh.from_pydata(vs, [], idx)
    mesh.uv_layers.new(name="UVMap").data.foreach_set("uv", np.array(us, np.float32).ravel())
    if len(ns) == len(vs):
        mesh.polygons.foreach_set("use_smooth", np.ones(len(mesh.polygons), bool))
        mesh.normals_split_custom_set(ns)
    mesh.materials.append(material(paint, vmat))
    scene.collection.objects.link(bpy.data.objects.new(paint, mesh))


for vmdl in MODELS:
    text = open(os.path.join(A, vmdl), encoding="utf-8").read()
    remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', text))
    for rel in [f for f in re.findall(r'filename = "([^"]+\.obj)"', text) if "hull" not in f]:
        path = os.path.join(A, rel)
        if MODE == "before" and rel.endswith("cerroblanco_fitout_fine.obj"):
            path = os.path.join(WORK, "before-install", "cerroblanco_fitout_fine.obj")
        if not os.path.exists(path):
            continue
        positions, uvs, normals, faces = read_obj(path)
        pts = np.array(positions)
        for paint, polys in faces.items():
            keep = []
            for poly in polys:
                q = pts[[int(t[0]) - 1 for t in poly]]
                low, high = q.min(0), q.max(0)
                # Anything starting above the ground floor goes, and flat faces up at the ceiling, so daylight gets in. Walls run on up past it, so they stay.
                if low[2] > Z1 or high[2] < Z0 or (high[2] > 100 and high[2] - low[2] < 1):
                    continue
                # The nearest point of the face's box, as a long wall's middle can be far from a spot on it.
                if (np.linalg.norm(np.clip(spots, low[:2], high[:2]) - spots, axis=1) < RADIUS).any():
                    keep.append(poly)
            if keep:
                make(paint, remaps.get(paint), keep, positions, uvs, normals)
if MODE == "after":
    text = open(os.path.join(A, "models/props/extinguisher-v2/extinguisher.vmdl"), encoding="utf-8").read()
    remaps = dict(re.findall(r'\{ from = "([^"]+)\.vmat" to = "([^"]+)" \}', text))
    positions, uvs, normals, faces = read_obj(os.path.join(A, "models/props/extinguisher-v2/extinguisher.obj"))
    transforms = [(p["yaw"], tuple(p["at"])) for p in places]
    for paint, polys in faces.items():
        make(paint, remaps.get(paint), polys, positions, uvs, normals, transforms)
    print("placed", len(transforms), flush=True)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.78, 0.85, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.1
scene.world = world
cam = bpy.data.cameras.new("camera")
cam.clip_start = 1.0
cam.clip_end = 8000
co = bpy.data.objects.new("camera", cam)
scene.collection.objects.link(co)
scene.camera = co
lamp = bpy.data.lights.new("fill", "AREA")
lamp.size = 120
lamp.energy = 900000
lo = bpy.data.objects.new("fill", lamp)
scene.collection.objects.link(lo)


def shoot(name, axis_xy, dist, side, height, aim, lens):
    place = next(p for p in places if abs(p["old_axis"][0] - axis_xy[0]) < 1 and abs(p["old_axis"][1] - axis_xy[1]) < 1)
    out = np.array(place["out"], float)
    right = np.array((out[1], -out[0]))
    wall = np.array(place["old_axis"][:2]) - out * 4.4
    eye = wall + out * dist + right * side
    co.location = (eye[0], eye[1], height)
    target = Vector((wall[0], wall[1], aim))
    co.rotation_euler = (target - co.location).to_track_quat("-Z", "Y").to_euler()
    cam.lens = lens
    lo.location = (eye[0] + right[0] * 40, eye[1] + right[1] * 40, 150)
    lo.rotation_euler = (target - lo.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x, scene.render.resolution_y = 1280, 800
    scene.render.filepath = os.path.join(OUT, f"{name}-{MODE}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, MODE, flush=True)


shoot("beside-a-painting", (40.0, -502.4), 58, 12, 62, 56, 30)
shoot("from-eye-height", (-102.0, 1103.6), 76, 18, 64, 56, 28)
shoot("in-the-room", (-1022.4, 972.0), 130, -36, 64, 52, 20)
print("done", flush=True)
