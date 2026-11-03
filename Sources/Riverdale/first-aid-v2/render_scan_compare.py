"""The installed paint and the scan-based trial on one wall, in Cycles, for when s&box can't be open: blender -b --factory-startup -t 4 --python render_scan_compare.py -- <work dir> <project root>

Writes compare_whole.png, compare_close_now.png and compare_close_scans.png into the work folder's blender/. Cycles flatters: this says how the two paints differ, and not how either looks in the game.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, ROOT = argv[0], argv[1]
OUT = os.path.join(WORK, "blender")
os.makedirs(OUT, exist_ok=True)
FOLDER = os.path.join(ROOT, "Assets", "models", "maps", "riverdale", "first_aid_v2")
SCANS = os.path.join(ROOT, "Assets", "materials", "forestbase", "scans")

bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "first_aid_build.blend"))
scene = bpy.context.scene
source = bpy.data.objects["first_aid_lod0"]
for ob in list(scene.objects):
    if ob is not source:
        bpy.data.objects.remove(ob)
source.data.materials.clear()
source.data.polygons.foreach_set("use_smooth", [True] * len(source.data.polygons))
source.data.set_sharp_from_angle(angle=math.radians(62))


def image(path, colour=False):
    img = bpy.data.images.load(path, check_existing=True)
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def pbr(name, folder, stem):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def tex(path, colour=False):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = image(path, colour)
        return node

    nt.links.new(tex(os.path.join(folder, f"{stem}_color.png"), True).outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(tex(os.path.join(folder, f"{stem}_rough.png")).outputs[0], bsdf.inputs["Roughness"])
    nt.links.new(tex(os.path.join(folder, f"{stem}_metal.png")).outputs[0], bsdf.inputs["Metallic"])
    normal = nt.nodes.new("ShaderNodeNormalMap")
    normal.uv_map = "UVMap"
    nt.links.new(tex(os.path.join(folder, f"{stem}_normal.png")).outputs[0], normal.inputs["Color"])
    nt.links.new(normal.outputs[0], bsdf.inputs["Normal"])
    return mat


def cabinet(name, y, mat):
    mesh = source.data.copy()
    mesh.materials.clear()
    mesh.materials.append(mat)
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (0.0, y, 0.0)
    scene.collection.objects.link(ob)
    return ob


NOW_Y, SCAN_Y = -10.5, 10.5
cabinet("now", NOW_Y, pbr("now", FOLDER, "first_aid"))
cabinet("scans", SCAN_Y, pbr("scans", os.path.join(FOLDER, "scanned"), "first_aid"))
bpy.data.objects.remove(source)

# A plain concrete wall from the project's scans, faced +X.
bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 8.5), rotation=(0, math.radians(90), 0))
wall = bpy.context.object
wall.scale = (120.0, 120.0, 1.0)
wall_mat = bpy.data.materials.new("wall")
wall_mat.use_nodes = True
nt = wall_mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
coords = nt.nodes.new("ShaderNodeTexCoord")
mapping = nt.nodes.new("ShaderNodeMapping")
mapping.inputs["Scale"].default_value = (2.2, 2.2, 1.0)
nt.links.new(coords.outputs["UV"], mapping.inputs["Vector"])
for suffix, slot, colour in (("diff", "Base Color", True), ("rough", "Roughness", False)):
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = image(os.path.join(SCANS, f"concrete_wall_007_{suffix}.jpg"), colour)
    nt.links.new(mapping.outputs[0], node.inputs["Vector"])
    nt.links.new(node.outputs[0], bsdf.inputs[slot])
wall.data.materials.append(wall_mat)

world = bpy.data.worlds.new("hall")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.66, 0.72, 1.0)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.55
scene.world = world
for location, power, size in (((70, -40, 90), 26000, 60), ((90, 50, 30), 7000, 80)):
    light = bpy.data.lights.new("area", "AREA")
    light.energy, light.size = power, size
    ob = bpy.data.objects.new("area", light)
    ob.location = location
    ob.rotation_euler = (Vector((0, 0, 8)) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(ob)

camera = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", camera)
scene.collection.objects.link(cam)
scene.camera = cam
camera.clip_start, camera.clip_end = 1.0, 2000.0
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "PNG"


def shot(name, eye, target, fov, w, h):
    cam.location = eye
    cam.rotation_euler = (Vector(target) - Vector(eye)).to_track_quat("-Z", "Y").to_euler()
    camera.angle = math.radians(fov)
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)


shot("compare_whole", (62, 0, 10), (3, 0, 8.3), 36, 1500, 800)
shot("compare_close_now", (20, NOW_Y + 3.5, 8), (5, NOW_Y + 1.5, 4.5), 46, 740, 520)
shot("compare_close_scans", (20, SCAN_Y + 3.5, 8), (5, SCAN_Y + 1.5, 4.5), 46, 740, 520)
print("compare done", flush=True)
