"""Quick Workbench looks at the built mast, for the author's own checking of the geometry while building (not review evidence).

blender -b --factory-startup --python preview.py -- <work dir> <lod> <out prefix> [view ...]
Views: full, base, hole, top, heads, head, back, lod.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1 :]
WORK, LOD, PREFIX = argv[0], int(argv[1]), argv[2]
VIEWS = argv[3:] or ["full", "base", "heads"]
bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "mast_build.blend"))
scene = bpy.context.scene
for ob in list(scene.objects):
    ob.hide_render = not (ob.name == f"mast_lod{LOD}")
shown = bpy.data.objects[f"mast_lod{LOD}"]
colours = {"mast_hw": (0.62, 0.64, 0.66, 1), "mast_pier": (0.45, 0.44, 0.42, 1), "mast_lens": (1.0, 0.85, 0.4, 1)}
TEXTURE = os.environ.get("MAST_TEX")
for m in shown.data.materials:
    m.diffuse_color = colours.get(m.name, (0.8, 0.8, 0.8, 1))
    if TEXTURE and m.name == "mast_hw":
        m.use_nodes = True
        m.node_tree.nodes.clear()
        node = m.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(TEXTURE)
        node.image.colorspace_settings.name = "sRGB"
        m.node_tree.nodes.active = node
scene.render.engine = "BLENDER_WORKBENCH"
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = "TEXTURE" if TEXTURE else "MATERIAL"
if os.environ.get("MAST_CULL"):
    # The engine culls back faces, so an inside-out or missing face shows as a hole here, as it would there.
    shading.show_backface_culling = True
    for m in bpy.data.materials:
        m.use_backface_culling = True
shading.show_cavity = False
scene.render.resolution_x, scene.render.resolution_y = 900, 1200
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Standard"
scene.world = bpy.data.worlds.new("w")
scene.world.color = (0.55, 0.6, 0.65)
cam_data = bpy.data.cameras.new("cam")
cam_data.angle = math.radians(40)
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
floor = bpy.data.meshes.new("floor")
floor.from_pydata([(-400, -400, 0), (400, -400, 0), (400, 400, 0), (-400, 400, 0)], [], [(0, 1, 2, 3)])
fo = bpy.data.objects.new("floor", floor)
scene.collection.objects.link(fo)
fm = bpy.data.materials.new("floor")
fm.diffuse_color = (0.3, 0.3, 0.3, 1)
floor.materials.append(fm)


def shot(name, eye, target, fov=40, size=(900, 1200)):
    scene.render.resolution_x, scene.render.resolution_y = size
    cam_data.angle = math.radians(fov)
    cam.location = Vector(eye)
    d = Vector(target) - Vector(eye)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(WORK, f"{PREFIX}_{name}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", name, flush=True)


# camera azimuth 214 degrees from the pole, as the capture camera has it
def ring(az, dist, z):
    a = math.radians(az)
    return (dist * math.cos(a), dist * math.sin(a), z)


for v in VIEWS:
    if v == "full":
        shot("full", ring(214, 520, 150), (0, 0, 150), fov=34, size=(700, 1200))
    elif v == "base":
        shot("base", ring(214, 90, 62), (0, 0, 28), fov=62, size=(1000, 800))
    elif v == "hole":
        shot("hole", ring(205, 30, 38), (0, 0, 36), fov=50, size=(900, 900))
    elif v == "top":
        shot("top", ring(214, 150, 300), (0, 0, 293), fov=50, size=(1000, 800))
    elif v == "heads":
        shot("heads", ring(10, 160, 290), (0, 0, 300), fov=62, size=(1200, 800))
    elif v == "head":
        shot("head", (70, 55, 300), (8, 35, 301), fov=48, size=(1000, 800))
    elif v == "back":
        shot("back", ring(190, 120, 300), (0, 0, 298), fov=60, size=(1200, 800))
    elif v == "lod":
        shot("lod", ring(214, 520, 150), (0, 0, 150), fov=34, size=(700, 1200))
    elif v == "cullcheck":
        # From inside the pole: with culling on, the pole's own inside faces vanish and the yard shows through.
        shot("cullcheck", (0, 0, 100), (40, 0, 100), fov=50, size=(700, 500))
    elif v == "under":
        shot("under", ring(150, 70, 255), (0, 0, 296), fov=70, size=(1000, 800))
    elif v == "plate":
        shot("plate", ring(232, 28, 64), (0, 0, 64), fov=40, size=(900, 700))
    elif v == "band":
        shot("band", ring(214, 70, 40), (0, 0, 32), fov=60, size=(1000, 1000))
    elif v == "mid":
        shot("mid", ring(214, 150, 120), (0, 0, 120), fov=60, size=(900, 1000))
print("preview done", flush=True)
