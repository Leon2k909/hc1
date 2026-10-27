"""Reduce already verified fir branch meshes for the background forest.

Run in Blender background mode; preserve OBJ axes, material names and source UVs.
"""
import bpy,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'Assets/models/maps/forestbase/fir'
statistics=[]
for variant in 'abc':
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials): bpy.data.materials.remove(material)
    bpy.ops.wm.obj_import(filepath=str(FOLDER/f'fir_{variant}_lod1.obj'),forward_axis='Y',up_axis='Z')
    meshes=[o for o in bpy.context.selected_objects if o.type=='MESH']
    bpy.context.view_layer.objects.active=meshes[0]
    if len(meshes)>1: bpy.ops.object.join()
    tree=bpy.context.view_layer.objects.active
    tree.data.calc_loop_triangles()
    original=len(tree.data.loop_triangles)
    # Uniform decimation thins the alpha-mapped needle cards disproportionately.
    # Preserve them; reduce the opaque bark and small dead-branch meshes instead.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL')
    bpy.ops.object.mode_set(mode='OBJECT')
    parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for part in parts:
        bpy.ops.object.select_all(action='DESELECT')
        part.select_set(True)
        bpy.context.view_layer.objects.active=part
        part.data.calc_loop_triangles()
        count=len(part.data.loop_triangles)
        material=part.material_slots[0].material.name
        if material.endswith('_twig'): continue
        target=1000 if material.endswith('_bark') else 300
        modifier=part.modifiers.new('Distant woody branch reduction','DECIMATE')
        modifier.ratio=min(1,target/count)
        modifier.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts: part.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    bpy.ops.object.join()
    tree=bpy.context.view_layer.objects.active
    tree.data.calc_loop_triangles()
    output=FOLDER/f'fir_{variant}_distant.obj'
    bpy.ops.wm.obj_export(filepath=str(output),export_selected_objects=True,
        apply_modifiers=True,export_triangulated_mesh=True,forward_axis='Y',up_axis='Z')
    lines=output.read_text().splitlines()
    assert any(line.startswith('vt ') for line in lines),'Missing source texture coordinates'
    assert not any('//' in line for line in lines if line.startswith('f '))
    vertices=[[float(x) for x in line.split()[1:]] for line in lines if line.startswith('v ')]
    statistics.append(dict(variant=variant,sourceTriangles=original,
        triangles=len(tree.data.loop_triangles),uvLayers=[x.name for x in tree.data.uv_layers],
        mins=[min(v[a] for v in vertices) for a in range(3)],
        maxs=[max(v[a] for v in vertices) for a in range(3)]))
    # Native material remaps provide all texture maps; avoid Blender map_Kd paths.
    mtl=output.with_suffix('.mtl')
    mtl.write_text('\n'.join(line for line in mtl.read_text().splitlines() if not line.startswith('map_'))+'\n')
    print(variant,statistics[-1]['triangles'],flush=True)
(ROOT/'output/forestbase/distant-fir-geometry.json').write_text(json.dumps(statistics,indent=2)+'\n')
