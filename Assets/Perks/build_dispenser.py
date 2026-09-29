"""Build the shared, game-scale geometry for the five perk dispensers.

Run with Blender: blender -b --python Assets/Perks/build_dispenser.py
The artwork is applied separately so every perk shares this silhouette.
"""
import bpy
from pathlib import Path

OUT = Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
parts = {}

def keep(obj, group):
    parts.setdefault(group, []).append(obj)
    return obj

def box(group, name, loc, size, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new('machined edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        obj.modifiers.new('weighted normals', 'WEIGHTED_NORMAL')
    return keep(obj, group)

def cylinder(group, name, loc, radius, depth, axis='Z', vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    obj.name = name
    if axis == 'X': obj.rotation_euler[1] = 1.57079632679
    if axis == 'Y': obj.rotation_euler[0] = 1.57079632679
    return keep(obj, group)

def card(group, name, x, half_width, bottom, top):
    # A +X facing quad with a 0-1 UV rectangle, for the per-perk artwork materials.
    verts = [(x,-half_width,bottom),(x,half_width,bottom),(x,half_width,top),(x,-half_width,top)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], [(0,1,2,3)])
    mesh.update()
    uv = mesh.uv_layers.new(name='UVMap')
    for loop_id, coord in zip(mesh.polygons[0].loop_indices, [(0,0),(1,0),(1,1),(0,1)]):
        uv.data[loop_id].uv = coord
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return keep(obj, group)

def arch(group, name, x_front, x_back, half_width, bottom, shoulder, top):
    # An octagonal shoulder makes a formed sheet-metal cabinet, not a capsule.
    yz = [(-half_width,bottom),(half_width,bottom),(half_width,shoulder),
          (half_width-4,top-4),(half_width-9,top),(-half_width+9,top),
          (-half_width+4,top-4),(-half_width,shoulder)]
    verts = [(x,y,z) for x in (x_back,x_front) for y,z in yz]
    faces = [tuple(reversed(range(8))),tuple(range(8,16))]
    faces += [(i,(i+1)%8,(i+1)%8+8,i+8) for i in range(8)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(obj)
    return keep(obj,group)

# Cast pedestal, deep side enclosure, formed shoulders, and top service cap.
box('dark','plinth', (0,0,5), (57,54,10), 2)
box('metal','plinth lower lip',(0,0,1.4),(59,56,2.8),1)
arch('enamel','formed cabinet',24,-25,26,10,72,88)
box('metal','top cap',(0,0,88),(49,39,3),1.5)
box('dark','top inset',(0,0,89.8),(42,32,1),.35)

# Side panels and their pressed ventilation slots are flush, not floating rails.
for side in (-1,1):
    box('metal',f'side inset {side}',(-4,side*26.15,45),(33,1.3,47),1)
    box('enamel',f'textured side plate {side}',(-4,side*26.85,45),(30,.35,44),.6)
    for z in (35,41,47,53):
        box('dark',f'side vent {side} {z}',(-6,side*27.1,z),(19,.45,1.5),.35)
    cylinder('metal',f'base bolt {side}',(19,side*22,8),1.4,1,'X',16)

# Front embossing: picture is seated within a thick gasket and brass bezel.
# The face of the image is at X=29.4, safely clear of the frame at X=29.2.
box('dark','upper panel well',(25.4,0,58),(3.0,36,49),2)
box('metal','display outer bezel',(27.2,0,58),(2.4,35,48),1.5)
box('dark','display gasket',(28.55,0,58),(1.1,30.8,43.8),.7)
# The poster (name plate, illustration, effect plate) is a 29.6 x 42.6 card; each perk gives it its own material.
card('card','poster',29.3,14.8,36.7,79.3)
for y in (-16.5,16.5):
    for z in (36,80):
        cylinder('dark',f'bezel rivet {y} {z}',(28.7,y,z),.65,.5,'X',12)

# A separate recessed dispensing bay below the illustration.
box('metal','lower moulding',(26.4,0,23.8),(3.6,38,19),2)
box('dark','dispensing cavity',(28.35,0,22.5),(1.2,25,12),1)
box('metal','tray rim',(31.0,0,15),(12,30,2.4),.8)
box('dark','tray catch',(30.3,0,16.4),(8,24,.55),.35)
cylinder('metal','tap mounting flange',(29.2,0,28.4),3,1.4,'X')
cylinder('metal','pour spout',(32.3,0,27.5),1.2,7.0,'X',24)
cylinder('dark','pour opening',(35.9,0,27.5),.8,.3,'X',24)

# A pressure dial, switch, and a compact color-lit indicator above the bay.
cylinder('metal','pressure gauge housing',(28.2,-12.5,30.7),3.3,1.6,'X')
cylinder('dark','gauge face',(29.1,-12.5,30.7),2.5,.2,'X')
box('metal','gauge needle',(29.3,-12.5,30.7),(.3,3.5,.35),.1)
cylinder('metal','selector surround',(28.5,12.5,30.7),2.8,1.5,'X')
cylinder('accent','illuminated switch',(29.5,12.5,30.7),1.5,.5,'X')
box('accent','status lamp',(27.4,0,84.4),(1.3,17,.9),.35)

# Lit name sign on the top cap, far enough forward that the cap's edge doesn't hide it from the player.
box('metal','sign frame',(18.5,0,96.4),(7,40,12.4),1)
box('dark','sign gasket',(22.0,0,96.4),(0.3,35.4,9.4),.1)
card('sign','sign glass',22.2,17,92.1,100.7)

# Merge each color/material group, retaining one renderer per surface type.
for group, objects in parts.items():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    joined = bpy.context.object
    joined.name = f'perk_{group}'
    if group == 'enamel':
        # Box projection gives the formed shoulders and both side panels stable,
        # correctly scaled UVs without stretching the texture across the shell.
        uv = joined.data.uv_layers.new(name='Enamel UV')
        for poly in joined.data.polygons:
            normal = poly.normal
            for loop_id in poly.loop_indices:
                xyz = joined.data.vertices[joined.data.loops[loop_id].vertex_index].co
                if abs(normal.x) >= abs(normal.y) and abs(normal.x) >= abs(normal.z):
                    coords = (xyz.y, xyz.z)
                elif abs(normal.y) >= abs(normal.z):
                    coords = (xyz.x, xyz.z)
                else:
                    coords = (xyz.x, xyz.y)
                uv.data[loop_id].uv = ((coords[0]+50)/90, coords[1]/90)
    bpy.ops.wm.obj_export(filepath=str(OUT / f'perk_{group}.obj'), export_selected_objects=True,
                          # s&box's OBJ importer treats OBJ coordinates as Y-up;
                          # convert Blender's Z-up geometry on export.
                          forward_axis='NEGATIVE_Z', up_axis='Y', export_materials=False,
                          apply_modifiers=True)
    # The enamel and lamps are tinted per perk at runtime; the poster and sign get per-perk material overrides.
    default_material = {'enamel': 'Perks/aged_enamel.vmat', 'accent': 'Perks/perk_lamp.vmat',
                        'card': 'Perks/boltsoda_poster.vmat', 'sign': 'Perks/boltsoda_sign.vmat'}.get(group, 'materials/default.vmat')
    (OUT / f'perk_{group}.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
 rootNode =
 {
  _class = "RootNode"
  children =
  [
   { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ ] use_global_default = true global_default_material = "''' + default_material + '''" } ] },
   { _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" filename = "Perks/perk_''' + group + '''.obj" import_translation = [ 0.0, 0.0, 0.0 ] import_rotation = [ 0.0, 0.0, 0.0 ] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" } ] },
  ]
  model_archetype = ""
  primary_associated_entity = ""
  base_model_name = ""
 }
}
''', encoding='utf-8')

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'perk_dispenser.blend'))
