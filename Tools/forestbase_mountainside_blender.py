"""Keep the scan's real proportions, origin and UVs while exporting three practical LODs."""
import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'Assets/models/maps/forestbase/mountainside'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'Sources/ForestBase/mountainside/source.gltf'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join()
obj=bpy.context.object
points=[obj.matrix_world@v.co for v in obj.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
origin=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
for v,p in zip(obj.data.vertices,points):v.co=p-origin
obj.matrix_world.identity()
obj.data.calc_loop_triangles();source_count=len(obj.data.loop_triangles)
statistics=[]
for lod,target in enumerate((24000,10000,3000)):
    bpy.ops.object.select_all(action='DESELECT')
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.scene.collection.objects.link(copy)
    bpy.context.view_layer.objects.active=copy;copy.select_set(True)
    modifier=copy.modifiers.new('LOD','DECIMATE');modifier.ratio=min(1,target/source_count)
    modifier.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=modifier.name)
    copy.data.calc_loop_triangles()
    bpy.ops.wm.obj_export(filepath=str(OUT/f'cliff_lod{lod}.obj'),export_selected_objects=True,
        export_materials=False,export_triangulated_mesh=True,global_scale=39.37007874,forward_axis='Z',up_axis='Y')
    statistics.append(dict(lod=lod,triangles=len(copy.data.loop_triangles),uvLayers=[l.name for l in copy.data.uv_layers]))
    bpy.data.objects.remove(copy,do_unlink=True)
(ROOT/'output/forestbase/mountainside-export.json').write_text(json.dumps(dict(sourceTriangles=source_count,sourceSizeMeters=list(hi-lo),lods=statistics),indent=2))
print('Mountainside physical dimensions:',list(hi-lo),flush=True)
