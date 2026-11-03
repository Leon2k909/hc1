"""Small CPU-only Blender preview of the actual new mesh and the old map crate.

blender -b --python render_preview.py -- <project-root>
"""
from pathlib import Path
from collections import Counter
import math
import sys
import ast
import types

import bpy
from mathutils import Vector
import numpy as np

ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
source = ast.parse((Path(__file__).parent / "build.py").read_text())
scope = dict(np=np, AW=2048, AH=2048, PPI=30, SLOTS=[(8 + k % 2 * 1024, 8 + k // 2 * 168) for k in range(24)])
definitions = [node for node in source.body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in ("unit", "Mesh", "build")]
exec(compile(ast.Module(body=definitions, type_ignores=[]), "crate-mesh", "exec"), scope)
B = types.SimpleNamespace(**scope)

OUT = ROOT / "output/asset-improvement-20261030/riverside-crate"
SCALE = .0254
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.resolution_x, scene.render.resolution_y = 1200, 850
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (.12, .12, .12)
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"


def image_node(mat, path, noncolor=False):
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        node.image.colorspace_settings.name = "Non-Color"
    return node


def material(name, colour=None, colorpath=None, normalpath=None, roughpath=None, metalpath=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Roughness"].default_value = .83
    if colour:
        # Blender's shader colour values are linear, while the engine's vmat colour tint is sRGB.
        shader.inputs["Base Color"].default_value = tuple(((c + .055) / 1.055) ** 2.4 if c > .04045 else c / 12.92 for c in colour) + (1,)
    for source, socket, noncolor in ((colorpath, "Base Color", False), (roughpath, "Roughness", True), (metalpath, "Metallic", True)):
        if source:
            node = image_node(mat, source, noncolor)
            mat.node_tree.links.new(node.outputs["Color"], shader.inputs[socket])
    if normalpath:
        node = image_node(mat, normalpath, True)
        normal = mat.node_tree.nodes.new("ShaderNodeNormalMap")
        mat.node_tree.links.new(node.outputs["Color"], normal.inputs["Color"])
        mat.node_tree.links.new(normal.outputs["Normal"], shader.inputs["Normal"])
    return mat


matdir = ROOT / "Assets/materials/riverside/crate_v2"
newmat = material("Supply crate v2", colorpath=matdir / "crate_color.png", normalpath=matdir / "crate_normal.png",
                  roughpath=matdir / "crate_rough.png", metalpath=matdir / "crate_metal.png")
oldmats = {
    "rs_crate": material("Original flat crate paint", colour=(.501961, .4, .274510)),
    "rs_wood": material("Original timber", colorpath=ROOT / "Assets/materials/riverside/rs_wood_color.jpg",
                        normalpath=ROOT / "Assets/materials/riverside/rs_wood_normal.jpg", roughpath=ROOT / "Assets/materials/riverside/rs_wood_rough.png"),
    "rs_signs": material("Original crate label", colorpath=ROOT / "Assets/materials/riverside/rs_signs_color.png"),
}


def mesh_object(name, points, faces, uvs, mats, indices=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(np.asarray(points) * SCALE, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    for mat in mats:
        mesh.materials.append(mat)
    layer = mesh.uv_layers.new()
    for p, coords in zip(mesh.polygons, uvs):
        if indices is not None:
            p.material_index = indices[p.index]
        for idx, uv in zip(p.loop_indices, coords):
            layer.data[idx].uv = uv
    return obj


mesh = B.build(0)
points = np.asarray(mesh.p).reshape(-1, 3)
uvs = np.asarray(mesh.t)
uvs = np.stack((uvs[:, :, 0] / B.AW, 1 - uvs[:, :, 1] / B.AH), -1)
new = mesh_object("New crate", points, np.arange(len(points)).reshape(-1, 3).tolist(), uvs, [newmat])

# The exact 86 old triangles removed only in the separate review copy of the pad.
oldlines = (ROOT / "Assets/models/maps/riverside/riverside_pad.obj").read_text().splitlines()
kept = Counter((ROOT / "Assets/models/props/riverside/crate_v2/review/pad_without_crate.obj").read_text().splitlines())
vertices, coords, faces, faceuvs, materials = [], [], [], [], []
current = None
yaw = math.atan2(-1, .3)
for line in oldlines:
    p = line.split()
    if not p:
        continue
    if p[0] == "v":
        x, y, z = float(p[3]) + 80, float(p[1]) + 140, float(p[2]) - 96
        vertices.append((x * math.cos(yaw) + y * math.sin(yaw), -x * math.sin(yaw) + y * math.cos(yaw), z))
    elif p[0] == "vt":
        coords.append(tuple(map(float, p[1:3])))
    elif p[0] == "usemtl":
        current = p[1]
    elif p[0] == "f":
        if kept[line]:
            kept[line] -= 1
            continue
        assert current in oldmats, current
        idx = [v.split("/") for v in p[1:]]
        faces.append([int(v[0]) - 1 for v in idx])
        faceuvs.append([coords[int(v[1]) - 1] for v in idx])
        materials.append(list(oldmats).index(current))
assert len(faces) == 86
old = mesh_object("Original crate", vertices, faces, faceuvs, list(oldmats.values()), materials)

bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.006))
ground = bpy.context.object
ground.data.materials.append(material("Matte studio floor", colour=(.19, .18, .16)))


def area(name, position, power, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.energy, data.shape, data.size, data.color = power, "DISK", size, color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector((0, 0, .3)) - obj.location).to_track_quat("-Z", "Y").to_euler()


area("Warm key", (1, -1.5, 2.5), 420, 2, (1, .86, .69))
area("Cool fill", (-1.5, -.3, 1.0), 90, 2.5, (.7, .82, 1))
area("Top edge", (.8, 2, 2), 280, 2, (1, .96, .9))
camera_data = bpy.data.cameras.new("Review camera")
camera = bpy.data.objects.new("Review camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.lens = 52
camera.data.clip_start = .01
camera.data.clip_end = 20
views = {"angle": ((49, -60, 44), (0, 0, 10)), "close": ((27, -37, 27), (0, -4, 10)), "back": ((-48, 57, 42), (0, 0, 10))}
variants = (("new", new),) if "--new-only" in sys.argv else (("old", old), ("new", new))
for variant, visible in variants:
    old.hide_render, new.hide_render = visible != old, visible != new
    for name, (eye, target) in views.items():
        camera.location = Vector(eye) * SCALE
        camera.rotation_euler = (Vector(target) * SCALE - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUT / f"studio-{variant}_{name}.png")
        bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "review.blend"))
