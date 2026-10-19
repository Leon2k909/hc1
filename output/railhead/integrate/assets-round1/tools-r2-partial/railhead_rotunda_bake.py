"""Bake the saved full Rotunde into Railhead's distant cutout using Blender.

Run Blender in background with --python Tools/railhead_rotunda_bake.py -- --stage <root> (reads the full model from the
stage and writes the cutout there; without --stage it reads and writes Assets).
Full model: models/maps/railhead/railhead_rotunda_full.vmdl (not referenced by Railhead).
The bake uses the existing model/materials, not an AI reinterpretation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
import railhead_render as R
from mathutils import Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = R.ASSETS
if "--stage" in argv:
    R.STAGE = Path(argv[argv.index("--stage") + 1]).resolve()
    OUT = R.STAGE
    if (R.STAGE / "scenes/maps/Railhead/railhead.scene").is_file():
        R.SCENE = R.STAGE / "scenes/maps/Railhead/railhead.scene"
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
for obj in R.map_model("models/maps/railhead/railhead_rotunda_full.vmdl"):
    obj.matrix_world = Matrix.Translation((-10400, 0, 700)) @ R.OBJ_TO_MODEL
# The original backdrop omits its buried underside. Close it for the cutout bake
# so the transparent region cannot reveal sky beneath the distant plinth.
drum_r = R.literal(R.ROOT / "Tools/railhead_backdrop.py", "ROTUNDA_R")
bpy.ops.mesh.primitive_cylinder_add(vertices=72, radius=drum_r + 10, depth=60, location=(-10400, 0, 670))
bpy.context.object.data.materials.append(R.material("materials/railhead/rw_dressed.vmat"))
found = R.read_scene()
import math
main_sun = 0.0
for world, colour in found["suns"]:
    R.add_sun(world, colour)
    main_sun = max(main_sun, max(colour[:3]))
# The park's warm bounce: the sunlit lawn and paths in front of the drum light its shaded north face from low down.
# A second sun from the north-north-east at 10 degrees, warm, 12% of the main sun.
fill = bpy.data.lights.new("Bounce", "SUN")
fill.color = (1.0, 0.88, 0.72)
fill.energy = math.pi * max(main_sun, 1.0) * 0.12
fill.angle = math.radians(20.0)
fill_obj = bpy.data.objects.new("Bounce", fill)
# From the NNE (plan e 0.38, n 0.92) at 10 degrees up; it shines the other way. World is ( north, -east, z ).
come = (0.92 * math.cos(math.radians(10)), -0.38 * math.cos(math.radians(10)), math.sin(math.radians(10)))
from mathutils import Vector
fill_obj.rotation_euler = (-Vector(come)).to_track_quat("-Z", "Y").to_euler()
scene.collection.objects.link(fill_obj)
if found["sky"]:
    sky = found["sky"][0]
    if isinstance(sky, dict):     # a resource reference saved as an object by the editor
        sky = next((v for v in sky.values() if isinstance(v, str) and v.endswith(".vmat")), None)
    if sky:
        R.add_sky(sky, 0)
# Parse constants without importing the generator (Blender does not bundle Pillow).
rotunda = R.literal(R.ROOT / "Tools/railhead_backdrop.py", "ROTUNDA")
base = 700.0
mid = base - 90 + R.literal(R.ROOT / "Tools/railhead_backdrop.py", "ROTUNDA_CARD_MID")
cam = R.set_camera((0, -3000, mid - 700), (0, rotunda[1], mid), 50)
cam.data.type = "ORTHO"
cam.data.ortho_scale = R.literal(R.ROOT / "Tools/railhead_backdrop.py", "ROTUNDA_CARD_SCALE")
scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.resolution_x, scene.render.resolution_y = 2048, 1024
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = 0.3       # the sun's and the bounce's shading in the card itself: a warm pale stone
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
(OUT / "materials/railhead").mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(OUT / "materials/railhead/rotunda_impostor.png")
bpy.ops.render.render(write_still=True)

# Pack a transparent border before making the Source 2 opacity mask. Without
# it, repeat sampling wraps the opaque bottom edge into a line above the roof.
import numpy as np
picture = bpy.data.images.load(scene.render.filepath, check_existing=False)
picture.scale(1920, 960)
inner = np.empty(1920 * 960 * 4, dtype=np.float32)
picture.pixels.foreach_get(inner)
inner = inner.reshape((960, 1920, 4))
# The camera looks up at it a little, as from the streets, so the drum's footing would show its underside (the buried
# closing disc) as an ellipse below the plinth. The park's land hides it from the streets: cut the cutout's alpha
# below the plinth's foot, the near half of its circle projected as the camera sees it.
from bpy_extras.object_utils import world_to_camera_view
foot = 700.0 + R.literal(R.ROOT / "Tools/railhead_backdrop.py", "ROTUNDA_FOOT")
cut = np.full(1920, -1, dtype=np.int64)          # first row (from the top) cut in each column
edge = drum_r + 10.0
for k in range(6001):                         # dense enough for every column (0.3 px per inch)
    e = edge * (2.0 * k / 6000 - 1.0)
    n_off = math.sqrt(max(edge * edge - e * e, 0.0))
    # world = ( north, -east, z ); the near side faces the station (north, +x)
    p = world_to_camera_view(scene, cam, Vector((-10400.0 + n_off, -e, foot)))
    col = int(round(p.x * 1920))
    row = int(round((1.0 - p.y) * 960)) + 1
    if 0 <= col < 1920:
        cut[col] = max(cut[col], row) if cut[col] >= 0 else row
for col in range(1920):
    if cut[col] >= 0:
        inner[: max(0, 960 - cut[col]), col, 3] = 0.0     # Blender's rows run from the bottom
padded = np.zeros((1024, 2048, 4), dtype=np.float32)
padded[32:992, 64:1984] = inner
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
mask.filepath_raw = str(OUT / "materials/railhead/rotunda_impostor_alpha.png")
mask.file_format = "PNG"
mask.save()
