from pathlib import Path
import json
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent/'construction-after'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'construction-detail.blend'))
scene = bpy.context.scene
camera = scene.camera
camera.location = Vector((40, -10, 61))*.0254
target = Vector((28, 23, 56))*.0254
camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.lens = 58
scene.cycles.samples = 12
scene.render.resolution_x = 1100
scene.render.resolution_y = 900
scene.render.filepath = str(OUT/'packet-detail.png')
bpy.ops.render.render(write_still=True)
(OUT/'packet-detail.json').write_text(json.dumps({
    'kind':'Blender construction render of the exact staged geometry',
    'native_engine_capture':False, 'camera_plan_inches':[40,-10,61],
    'target_plan_inches':[28,23,56], 'lens_mm':58,
    'saved_geometry':'construction-detail.blend'
}, indent=2)+'\n')
