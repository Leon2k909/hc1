"""Run in Blender on the downloaded CC0 source to inspect/export authored tree LODs."""
import bpy, json
from pathlib import Path
root=Path(__file__).resolve().parent.parent
out=root/'output/forestbase/pine-blend-info.json'
info=[]
for obj in bpy.data.objects:
    info.append(dict(name=obj.name,type=obj.type,polygons=len(obj.data.polygons) if obj.type=='MESH' else 0,
                     collections=[c.name for c in obj.users_collection],modifiers=[(m.name,m.type) for m in obj.modifiers]))
out.write_text(json.dumps(info,indent=2))

# The source's LOD2 still contains hundreds of thousands of individual needle polygons.
# Produce three useful game LODs, keeping its original crown/branch silhouette and UVs.
folder=root/'Assets/models/maps/forestbase/pine'
folder.mkdir(parents=True,exist_ok=True)
for obj in list(bpy.data.objects):
    if obj.type=='MESH' and not obj.name.endswith('LOD2'):
        mesh=obj.data; bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0: bpy.data.meshes.remove(mesh)
bpy.ops.object.select_all(action='DESELECT')
statistics=[]
for variant in 'abc':
    original=bpy.data.objects.get(f'pine_tree_01_{variant}_LOD2')
    if original is None: continue
    original.hide_set(False); original.hide_viewport=False
    for collection in original.users_collection: collection.hide_viewport=False
    for lod,ratio in enumerate((.24,.10,.018)):
        obj=original.copy(); obj.data=original.data.copy(); bpy.context.scene.collection.objects.link(obj)
        obj.name=f'pine_{variant}_lod{lod}'; obj.location=(0,0,0)
        bpy.context.view_layer.objects.active=obj; obj.select_set(True)
        mod=obj.modifiers.new('Gameplay LOD','DECIMATE'); mod.ratio=ratio; mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.wm.obj_export(filepath=str(folder/f'pine_{variant}_lod{lod}.obj'),export_selected_objects=True,
            apply_modifiers=True,export_materials=True,export_triangulated_mesh=True,
            global_scale=39.37007874,forward_axis='Z',up_axis='Y')
        # ModelDoc remaps every material to the bundled VMAT. Do not ship Blender's
        # absolute source-machine texture paths in the auxiliary material library.
        mtl=folder/f'pine_{variant}_lod{lod}.mtl'
        mtl.write_text('\n'.join(line for line in mtl.read_text().splitlines()
                                if not line.startswith('map_'))+'\n')
        statistics.append(dict(name=obj.name,faces=len(obj.data.polygons)))
        data=obj.data; bpy.data.objects.remove(obj,do_unlink=True); bpy.data.meshes.remove(data)
(root/'output/forestbase/pine-lods.json').write_text(json.dumps(statistics,indent=2))
