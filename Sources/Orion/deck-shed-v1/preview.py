"""Quick Workbench looks at the built shed, for the author's own checking of the geometry while building (not review evidence).

blender -b --factory-startup --python preview.py -- <work dir> <out prefix> [view ...]
Views: front, left, right, back, roof, east, west, cabinet, louvre, eave, base, boot.
Each part is tinted by the key the build stored on it, so overlapping or doubled parts show up; MAST_CULL=1 turns back faces off
the way the engine does, so an inside-out or missing face shows as a hole.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, PREFIX = argv[0], argv[1]
VIEWS = argv[2:] or ["front", "left", "right", "back", "roof"]
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "shed_build.blend"))
scene = bpy.context.scene
LOD = int(os.environ.get("SHED_LOD", "-1"))
shown_name = "shed_bake" if LOD < 0 else f"shed_lod{LOD}"
for ob in list(scene.objects):
    ob.hide_render = ob.name != shown_name
shown = bpy.data.objects[shown_name]
scene.render.engine = "BLENDER_WORKBENCH"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "VERTEX" if LOD < 0 else "MATERIAL"
if LOD >= 0:
    for m in shown.data.materials:
        m.diffuse_color = (0.62, 0.64, 0.66, 1)
if os.environ.get("MAST_CULL"):
    shading.show_backface_culling = True
    for m in bpy.data.materials:
        m.use_backface_culling = True
shading.show_cavity = False
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.55, 0.6, 0.65)
cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
floor = bpy.data.meshes.new("floor")
floor.from_pydata([(-600, -600, 0), (600, -600, 0), (600, 600, 0), (-600, 600, 0)], [], [(0, 1, 2, 3)])
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)
fm = bpy.data.materials.new("floor")
fm.diffuse_color = (0.3, 0.3, 0.3, 1)
floor.materials.append(fm)


def shot(name, eye, target, fov=40, size=(1100, 800)):
    scene.render.resolution_x, scene.render.resolution_y = size
    cam_data.angle = math.radians(fov)
    cam.location = Vector(eye)
    d = Vector(target) - Vector(eye)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(WORK, f"{PREFIX}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)


def ring(az, dist, z):
    """az 0 = from the front (south, -X), 90 = from the west (+Y), 180 = from the back, 270 = from the east."""
    a = math.radians(az)
    return (-dist * math.cos(a), dist * math.sin(a), z)


for v in VIEWS:
    if v == "front":
        shot("front", ring(0, 330, 64), (-45, 0, 56), fov=44)
    elif v == "left":
        shot("left", ring(40, 330, 70), (0, 0, 55), fov=44)
    elif v == "right":
        shot("right", ring(320, 330, 70), (0, 0, 55), fov=44)
    elif v == "back":
        shot("back", ring(180, 330, 80), (0, 0, 55), fov=44)
    elif v == "roof":
        shot("roof", ring(25, 240, 360), (0, 0, 108), fov=48)
    elif v == "east":
        shot("east", ring(270, 330, 70), (0, 0, 55), fov=44)
    elif v == "west":
        shot("west", ring(90, 330, 70), (0, 0, 55), fov=44)
    elif v == "cabinet":
        shot("cabinet", (-170, -60, 70), (-48, -38, 66), fov=42)
    elif v == "louvre":
        shot("louvre", (-170, 55, 70), (-48, 40, 72), fov=42)
    elif v == "eave":
        shot("eave", (-120, -30, 150), (-45, -30, 104), fov=48)
    elif v == "base":
        shot("base", (-130, 60, 30), (-45, 40, 6), fov=50)
    elif v == "boot":
        shot("boot", (0, -190, 60), (19, -60, 24), fov=44)
    elif v == "door":
        shot("door", (-150, 0, 80), (-45, 0, 70), fov=46)
print("preview done", flush=True)
