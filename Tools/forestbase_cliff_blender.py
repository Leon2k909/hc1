"""Blender stage: normalize a scanned cliff to a reusable 2x2x1 unit module."""
import bpy, json, sys
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent.parent
kind=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'cliff'
folder=root/f'Assets/models/maps/forestbase/{kind}'
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(root/f'Sources/ForestBase/{kind}/cliff.gltf'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0]; bpy.ops.object.join()
original=bpy.context.object
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=.00001)
bpy.ops.object.mode_set(mode='OBJECT')
points=[original.matrix_world@v.co for v in original.data.vertices]
lo=Vector(tuple(min(p[i] for p in points) for i in range(3))); hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
for v in original.data.vertices:
    p=original.matrix_world@v.co
    v.co=Vector(((p.x-(lo.x+hi.x)/2)/(hi.x-lo.x)*2,(p.y-(lo.y+hi.y)/2)/(hi.y-lo.y)*2,(p.z-lo.z)/(hi.z-lo.z)))
original.matrix_world.identity()
statistics=[]
for lod,ratio in enumerate((.18,.06,.015) if kind=='boulder' else (.09,.025,.006)):
    bpy.ops.object.select_all(action='DESELECT')
    obj=original.copy(); obj.data=original.data.copy(); bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj; obj.select_set(True)
    mod=obj.modifiers.new('LOD','DECIMATE'); mod.ratio=ratio; mod.use_collapse_triangulate=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.wm.obj_export(filepath=str(folder/f'cliff_lod{lod}.obj'),export_selected_objects=True,export_materials=False,
        export_triangulated_mesh=True,forward_axis='Z',up_axis='Y')
    statistics.append(dict(lod=lod,triangles=len(obj.data.polygons)))
    bpy.data.objects.remove(obj,do_unlink=True)
(root/f'output/forestbase/{kind}-lods.json').write_text(json.dumps(statistics,indent=2))
