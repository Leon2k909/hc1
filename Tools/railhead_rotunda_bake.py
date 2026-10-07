"""Bake the saved full Rotunde into Railhead's distant cutout using Blender.

Run Blender in background with --python Tools/railhead_rotunda_bake.py.
Full model: models/maps/railhead/railhead_rotunda_full.vmdl (not referenced by Railhead).
The bake uses the existing model/materials, not an AI reinterpretation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import railhead_render as R
from mathutils import Matrix

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for obj in R.map_model("models/maps/railhead/railhead_rotunda_full.vmdl"):
    obj.matrix_world = Matrix.Translation((-10400, 0, 700)) @ R.OBJ_TO_MODEL
# The original backdrop omits its buried underside. Close it for the cutout bake
# so the transparent region cannot reveal sky beneath the distant plinth.
bpy.ops.mesh.primitive_cylinder_add(vertices=72, radius=2110, depth=60, location=(-10400, 0, 670))
bpy.context.object.data.materials.append(R.material("materials/railhead/rw_dressed.vmat"))
found = R.read_scene()
for world, colour in found["suns"]:
    R.add_sun(world, colour)
if found["sky"]:
    R.add_sky(found["sky"][0], 0)
# Parse constants without importing the generator (Blender does not bundle Pillow).
rotunda = R.literal(R.ROOT / "Tools/railhead_backdrop.py", "ROTUNDA")
base = 700.0
mid = base - 90 + 1250
cam = R.set_camera((0, -3000, mid - 1500), (0, rotunda[1], mid), 50)
cam.data.type = "ORTHO"
cam.data.ortho_scale = 5000
scene.render.engine = "CYCLES"
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.resolution_x, scene.render.resolution_y = 2048, 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = -1
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = str(R.ASSETS / "materials/railhead/rotunda_impostor.png")
bpy.ops.render.render(write_still=True)

# Pack a transparent border before making the Source 2 opacity mask. Without
# it, repeat sampling wraps the opaque bottom edge into a line above the roof.
import numpy as np
picture = bpy.data.images.load(scene.render.filepath, check_existing=False)
picture.scale(1920, 960)
inner = np.empty(1920 * 960 * 4, dtype=np.float32)
picture.pixels.foreach_get(inner)
padded = np.zeros((1024, 2048, 4), dtype=np.float32)
padded[32:992, 64:1984] = inner.reshape((960, 1920, 4))
picture = bpy.data.images.new("Rotunde padded", width=2048, height=1024)
picture.pixels.foreach_set(padded.ravel())
picture.filepath_raw = scene.render.filepath
picture.file_format = "PNG"
picture.save()
# Pack a separate opacity mask for the Source 2 material compiler.
pixels = np.empty(2048 * 1024 * 4, dtype=np.float32)
picture.pixels.foreach_get(pixels)
rgba = pixels.reshape((-1, 4))
rgba[:, :3] = (rgba[:, 3:4] >= 0.8).astype(np.float32)
rgba[:, 3] = 1
mask = bpy.data.images.new("Rotunde opacity", width=2048, height=1024)
mask.colorspace_settings.name = "Non-Color"
mask.pixels.foreach_set(pixels)
mask.filepath_raw = str(R.ASSETS / "materials/railhead/rotunda_impostor_alpha.png")
mask.file_format = "PNG"
mask.save()
