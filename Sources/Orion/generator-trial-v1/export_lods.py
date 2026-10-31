"""Export the approved editable model at three lower detail levels; never edit Assets."""
from pathlib import Path
import bpy,json,sys,shutil
HERE=Path(__file__).parent;ROOT=HERE.parents[2]
OUT=ROOT/'output/orion-generator-installed-20261030';RAW=OUT/'raw';RAW.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(HERE/'generator_review.blend'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render and o.name!='Same neutral floor']
assert parts and not any(o.name.startswith('Actual installed') for o in parts)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.hide_set(False);o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();base=bpy.context.object
shutil.copy2(HERE/'generator_after.obj',RAW/'lod0.obj')
shutil.copy2(HERE/'generator_after.mtl',RAW/'lod0.mtl')
report={'lodTriangles':[51658]}
for lod,ratio in enumerate((.40,.14,.045),1):
    bpy.ops.object.select_all(action='DESELECT');obj=base.copy();obj.data=base.data.copy();bpy.context.collection.objects.link(obj)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Distant detail reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    count=sum(len(p.vertices)-2 for p in obj.data.polygons);report['lodTriangles'].append(count)
    bpy.ops.wm.obj_export(filepath=str(RAW/f'lod{lod}.obj'),export_selected_objects=True,forward_axis='NEGATIVE_Y',up_axis='Z',export_triangulated_mesh=True)
    bpy.data.objects.remove(obj,do_unlink=True)
(OUT/'lod-export.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
