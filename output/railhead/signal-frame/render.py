"""CPU PBR inspection of the actual exported meshes; not an in-game capture."""
from pathlib import Path
import math
import re
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "Assets"
OUT = Path(__file__).resolve().parent
CORE = Path("D:/SteamLibrary/steamapps/common/sbox/core")
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.view_settings.exposure = .15
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (.53, .67, .86, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = .33


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def load(mesh, translation=(0, 0, 0)):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(mesh), forward_axis="NEGATIVE_Z", up_axis="Y")
    new = set(bpy.data.objects) - before
    for o in new:
        o.scale = (.0254,) * 3
        o.location = Vector(translation) * .0254
    print("Imported", mesh.name, len(new), flush=True)


load(ASSETS / "models/maps/railhead/railhead_centre.obj")
load(ASSETS / "models/maps/railhead/railhead_glass.obj")
load(ASSETS / "models/maps/railhead/railhead_track.obj")
load(ASSETS / "models/props/railhead/signal_frame/signal_frame.obj", (0, 2160, 130))

remaps = {}
for file in (ASSETS / "models/maps/railhead/railhead_centre.vmdl",
             ASSETS / "models/maps/railhead/railhead_glass.vmdl",
             ASSETS / "models/maps/railhead/railhead_track.vmdl",
             ASSETS / "models/props/railhead/signal_frame/signal_frame.vmdl"):
    remaps.update({a.removesuffix(".vmat"): b for a, b in re.findall(r'from = "([^"]+)" to = "([^"]+)"', file.read_text())})
image_cache = {}


def texture(nodes, links, path, target, socket, space="sRGB"):
    if path.startswith("["):
        return
    absolute = ASSETS / path
    if not absolute.exists():
        absolute = CORE / path
    if not absolute.exists():
        print("Missing preview texture", path, flush=True)
        return
    key = (str(absolute), space)
    if key not in image_cache:
        image_cache[key] = bpy.data.images.load(str(absolute), check_existing=False)
        image_cache[key].colorspace_settings.name = space
    n = nodes.new("ShaderNodeTexImage")
    n.image = image_cache[key]
    links.new(n.outputs["Color"], target.inputs[socket])


for mat in bpy.data.materials:
    name = re.sub(r"\.\d+$", "", mat.name).removesuffix(".vmat")
    path = ASSETS / remaps.get(name, f"materials/railhead/{name}.vmat")
    if not path.exists():
        path = CORE / remaps.get(name, f"materials/railhead/{name}.vmat")
    data = path.read_text() if path.exists() else ""
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    p = nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = (.18, .18, .16, 1)
    p.inputs["Roughness"].default_value = .55
    links.new(p.outputs[0], output.inputs[0])
    for field, socket in (("TextureColor", "Base Color"), ("TextureRoughness", "Roughness"), ("TextureMetalness", "Metallic")):
        found = re.search(rf'{field}\s+"([^"]+)"', data)
        if found:
            texture(nodes, links, found[1], p, socket, "sRGB" if field == "TextureColor" else "Non-Color")
    normal = re.search(r'TextureNormal\s+"([^"]+)"', data)
    if normal:
        nm = nodes.new("ShaderNodeNormalMap")
        texture(nodes, links, normal[1], nm, "Color", "Non-Color")
        links.new(nm.outputs[0], p.inputs["Normal"])
    value = re.search(r'g_flMetalness\s+"([^"]+)"', data)
    if value:
        p.inputs["Metallic"].default_value = float(value[1])
    if "glass" in name.lower() or 'F_TRANSLUCENT "1"' in data:
        # The map's canopy/cabin glass is a thin pane, not a solid dark volume.
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = .035
        links.new(transparent.outputs[0], mix.inputs[1])
        links.new(p.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs[0])
        p.inputs["Roughness"].default_value = .12
    if name == "rw_signal_frame_amber":
        p.inputs["Base Color"].default_value = (1, .42, .02, 1)
        p.inputs["Emission Color"].default_value = (1, .42, .02, 1)
        p.inputs["Emission Strength"].default_value = 4
    if name == "rw_signal_frame_bulb":
        p.inputs["Base Color"].default_value = (1, .73, .36, 1)
        p.inputs["Emission Color"].default_value = (1, .73, .36, 1)
        p.inputs["Emission Strength"].default_value = 2.3
    print("Material", name, path.exists(), flush=True)


def light(name, kind, position, power, color=(1, .85, .64), target=None, size=1):
    data = bpy.data.lights.new(name, kind)
    data.energy = power
    data.color = color
    if kind == "AREA":
        data.shape = "RECTANGLE"
        data.size = size
        data.size_y = size * .35
    if kind == "POINT":
        data.shadow_soft_size = .022
    o = bpy.data.objects.new(name, data)
    scene.collection.objects.link(o)
    o.location = Vector(position) * .0254
    if target:
        aim(o, Vector(target) * .0254)
    return o


sun = light("Afternoon sun", "SUN", (-320, 2600, 780), 2.2, (1, .84, .65), (100, 1950, 0))
sun.data.angle = .018
light("Broad sky at front windows", "AREA", (0, 2230, 227), 650, (.76, .85, 1), (0, 2040, 170), 6)
light("Side-window bounce", "AREA", (-155, 2050, 209), 150, (.86, .88, 1), (0, 2140, 160), 3)
for e, n in ((30, -1960), (35, -2040), (20, -2120)):
    light("Warm pendant", "POINT", (-e, -n, 212.3), 60, (1, .65, .29))

camera_data = bpy.data.cameras.new("Signal frame inspection")
camera = bpy.data.objects.new("Signal frame inspection", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.clip_start = .01
camera_data.clip_end = 500
camera_data.lens = 24
camera.location = Vector((0, 1989, 189)) * .0254
aim(camera, Vector((0, 2160, 181)) * .0254)
scene.render.filepath = str(OUT / "signal_frame_room.png")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "signal_frame_preview.blend"))
bpy.ops.render.render(write_still=True)
print("Room preview complete", flush=True)
camera_data.lens = 48
camera.location = Vector((-38, 2070, 178)) * .0254
aim(camera, Vector((-24, 2160, 174)) * .0254)
scene.render.resolution_x = 1300
scene.render.resolution_y = 1000
scene.render.filepath = str(OUT / "signal_frame_detail.png")
bpy.ops.render.render(write_still=True)
print("Detail preview complete", flush=True)
