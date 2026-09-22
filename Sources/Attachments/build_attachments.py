"""Build the HC1 cosmetic attachment meshes. Run with Blender 5.x --background --python.

Coordinates are Source game units: +X forward, +Z up. Suppressor origin is the
rear mounting face; grip origin is the centre of the rail contact surface.
These are game-art shells, with no functional internals or engineering drawings.
"""
import bpy
import bmesh
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "Assets/attachments/hc1"
SOURCE = ROOT / "Sources/Attachments"
QA = SOURCE / "qa"
ATLAS = ASSETS / "textures/hc1_attachment_atlas_color.png"
SPECS = {
    "anodized": ((0.0, 0.5), 0.78, 0.46),
    "polymer": ((0.5, 0.5), 0.0, 0.78),
    "steel": ((0.0, 0.0), 0.94, 0.32),
    "ceramic": ((0.5, 0.0), 0.18, 0.66),
}
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    if collection.name != 'Collection':
        bpy.data.collections.remove(collection)
bpy.context.scene.unit_settings.system = 'NONE'
bpy.context.preferences.filepaths.save_version = 0
QA.mkdir(parents=True, exist_ok=True)
image = bpy.data.images.load(str(ATLAS), check_existing=True)
materials = {}
for key, (quadrant, metalness, roughness) in SPECS.items():
    mat = bpy.data.materials.new('hc1_' + key)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metalness
    bsdf.inputs['Roughness'].default_value = roughness
    texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    mat.node_tree.links.new(texture.outputs['Color'], bsdf.inputs['Base Color'])
    materials[key] = mat
    folder = ASSETS / 'materials'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'hc1_{key}.vmat').write_text(f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "0"
    g_flMetalness "{metalness}"
    g_flRoughnessScaleFactor "{roughness}"
    TextureColor "attachments/hc1/textures/hc1_attachment_atlas_color.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "materials/default/default_rough.tga"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1.0 1.0 1.0 1.0]"
    g_flModelTintAmount "1.0"
}}
''', encoding='utf-8')

parts = {}
active_objects = []


def finish(obj, name, material, bevel=0.03):
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(materials[material])
    obj['surface'] = material
    if bevel:
        mod = obj.modifiers.new('Machined edge radii', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
    normal = obj.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
    normal.keep_sharp = True
    normal.weight = 50
    active_objects.append(obj)
    return obj


def box(name, loc, size, material='anodized', bevel=0.045):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.dimensions = size
    return finish(obj, name, material, bevel)


def cylinder(name, loc, radius, depth, material='steel', axis='X', vertices=48, bevel=0.015):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj = bpy.context.object
    if axis == 'X':
        obj.rotation_euler.y = math.pi / 2
    elif axis == 'Y':
        obj.rotation_euler.x = math.pi / 2
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return finish(obj, name, material, bevel)


def shell(name, profile, material='anodized', sides=48):
    # A revolved closed wall section: exterior, front lip, interior return, rear lip.
    verts = [(x, r*math.cos(a*math.tau/sides), r*math.sin(a*math.tau/sides))
             for x, r in profile for a in range(sides)]
    faces = []
    for row in range(len(profile)):
        nxt = (row + 1) % len(profile)
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((row*sides+i, row*sides+j, nxt*sides+j, nxt*sides+i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    # Recalculate normals before beveling the closed shell.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    for face in mesh.polygons:
        face.use_smooth = True
    finish(obj, name, material, 0.008)
    obj.modifiers['Machined edge radii'].segments = 1
    return obj


def ring(name, x, length, radius, material='steel', inner=None):
    inner = inner if inner is not None else radius - 0.06
    return shell(name, [(x, radius), (x+length, radius), (x+length, inner), (x, inner)], material)


def bolt(name, x, y, z):
    cylinder(name + '_washer', (x, y, z), 0.14, 0.045, 'steel', 'Y', 32)
    head = cylinder(name + '_head', (x, y*1.02, z), 0.10, 0.08, 'anodized', 'Y', 6, 0.008)
    return head


def rail_mount(length=1.75):
    box('rail_saddle', (0, 0, -0.17), (length, 0.88, 0.30), bevel=0.035)
    for sign in [-1, 1]:
        jaw = box('clamp_jaw', (0, sign*0.46, -0.16), (length, 0.17, 0.32), bevel=0.025)
        jaw.rotation_euler.x = sign*0.22
        for x in [-length*0.28, length*0.28]:
            bolt('clamp_fastener', x, sign*0.57, -0.19)
    box('cross_key', (0, 0, -0.01), (0.13, 0.66, 0.08), 'steel', 0.01)


def extruded_profile(name, profile, halfwidth, material='polymer', bevel=0.07):
    count = len(profile)
    verts = [(x, y, z) for y in [-halfwidth, halfwidth] for x, z in profile]
    faces = [tuple(reversed(range(count))), tuple(range(count, 2*count))]
    faces.extend((i, (i+1)%count, (i+1)%count+count, i+count) for i in range(count))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return finish(obj, name, material, bevel)


def beam(name, a, b, width, depth, material='polymer'):
    a, b = Vector(a), Vector(b)
    obj = box(name, (a+b)/2, (width, depth, (b-a).length), material, 0.065)
    obj.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    return obj


def suppressor(compact=False):
    length, r = (4.7, 0.64) if compact else (6.6, 0.78)
    shell('outer_can', [(0.5, r*0.89), (0.72, r), (length-0.25, r),
                       (length-0.07, r*0.93), (length-0.07, r*0.70),
                       (0.62, r*0.70), (0.5, r*0.74)], 'ceramic' if compact else 'anodized')
    ring('rear_socket', -0.25, 0.85, r*0.72, 'steel', r*0.42)
    ring('locking_collar', 0.02, 0.51, r*0.94, 'anodized', r*0.70)
    for i in range(16):
        angle = math.tau*i/16
        obj = box('collar_flute', (0.265, r*0.94*math.cos(angle), r*0.94*math.sin(angle)),
                  (0.34, 0.07, 0.10), 'anodized', 0.018)
        obj.rotation_euler.x = angle
    ring('shoulder_band', 0.66, 0.13, r+0.023, 'steel')
    ring('front_band', length-0.4, 0.10, r+0.016, 'anodized')
    # Recessed front aperture and visible lip, without functional internals.
    shell('end_cap', [(length-0.16,r*0.86),(length,r*0.82),(length,0.205),
                      (length-0.27,0.205),(length-0.27,r*0.68)], 'steel')
    for i in range(8):
        angle = math.tau*i/8
        cylinder('cap_recess', (length+0.004, r*0.64*math.cos(angle), r*0.64*math.sin(angle)),
                 0.041, 0.013, 'anodized', vertices=12, bevel=0.004)
    for x in ([1.1,1.27,3.95,4.1] if compact else [1.18,1.34,5.85,6.02]):
        ring('witness_groove', x, 0.028, r+0.006, 'anodized')
    # Small modelled side plate, recessed-looking pin pair, no baked hardware.
    box('identification_plate', (length*0.49,-r-0.005,0), (1.22,0.027,0.24), 'anodized',0.005)
    for x in [length*0.49-0.48, length*0.49+0.48]:
        cylinder('plate_pin',(x,-r-0.029,0),0.031,0.018,'steel','Y',16,0.003)
    return length


def vertical_grip():
    rail_mount()
    profile = [(-0.57,-0.29),(0.54,-0.29),(0.53,-0.70),(0.39,-1.00),
               (0.31,-3.37),(0.48,-3.52),(0.44,-3.77),(-0.48,-3.77),
               (-0.56,-3.52),(-0.48,-1.1),(-0.65,-0.69)]
    extruded_profile('grip_body', profile, 0.40, 'polymer')
    box('heel_cap',(-0.01,0,-3.66),(0.93,0.82,0.22),'anodized',0.08)
    for side in [-1,1]:
        box('inset_grip_panel',(-0.07,side*0.404,-2.15),(0.66,0.052,1.89),'polymer',0.09)
        for i in range(7):
            box('traction_rib',(-0.07,side*0.444,-1.35-i*0.235),(0.59,0.058,0.065),'polymer',0.019)
    cylinder('heel_fastener',(-0.02,0,-3.789),0.15,0.025,'steel','Z',8,0.008)


def angled_grip():
    rail_mount(2.9)
    extruded_profile('front_hand_stop',[(0.99,-0.29),(1.43,-0.29),(1.48,-1.44),
                                      (1.20,-1.71),(0.94,-1.60)],0.40,'ceramic')
    # Open centre is actual silhouette geometry, with a sloped lower support.
    beam('rear_support',(-1.27,0,-0.28),(-0.57,0,-1.31),0.35,0.66,'ceramic')
    beam('sloped_palm_shelf',(-0.65,0,-1.28),(1.19,0,-1.72),0.34,0.83,'polymer')
    for i in range(9):
        t=i/8
        x=-0.47+t*1.53
        z=-1.41-t*0.367
        pad = box('palm_traction', (x,0,z), (0.072,0.87,0.065),'polymer',0.016)
        pad.rotation_euler.y=0.235
    for side in [-1,1]:
        bolt('handstop_pivot',1.20,side*0.43,-1.32)


def prepare_objects(objects):
    for obj in objects:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        # Thin bevelled panels can leave collinear triangles at their corners.
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        flat = [face for face in bm.faces if face.calc_area() < 1e-7]
        if flat:
            bmesh.ops.delete(bm, geom=flat, context='FACES')
        bm.to_mesh(obj.data)
        bm.free()
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.025)
        bpy.ops.object.mode_set(mode='OBJECT')
        offset = SPECS[obj['surface']][0]
        for loop in obj.data.uv_layers.active.data:
            loop.uv.x = offset[0]+0.02+loop.uv.x*0.46
            loop.uv.y = offset[1]+0.02+loop.uv.y*0.46


def export_obj(name, objects):
    path=ASSETS/name
    path.mkdir(parents=True,exist_ok=True)
    lines=[f'# HC1 {name}: +X forward, +Z up; game-art only',f'mtllib {name}.mtl']
    index=1
    tri_count=0
    bounds=[]
    used=set()
    for obj in objects:
        mesh=obj.data
        mesh.calc_loop_triangles()
        uv=mesh.uv_layers.active.data
        lines.extend([f'o {obj.name}',f'usemtl {obj.data.materials[0].name}'])
        used.add(obj['surface'])
        normals=mesh.corner_normals
        for tri in mesh.loop_triangles:
            tri_count+=1
            for li in tri.loops:
                v=obj.matrix_world@mesh.vertices[mesh.loops[li].vertex_index].co
                n=(obj.matrix_world.to_3x3()@normals[li].vector).normalized()
                t=uv[li].uv
                bounds.append(tuple(v))
                # ModelDoc's OBJ importer converts (x,y,z) to (z,x,y).
                # Counter that here; Blender and the compiled VMDL then agree.
                lines.extend([f'v {v.y:.7f} {v.z:.7f} {v.x:.7f}',
                              f'vt {t.x:.7f} {t.y:.7f}',f'vn {n.y:.7f} {n.z:.7f} {n.x:.7f}'])
            lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(index,index+3)))
            index+=3
    (path/f'{name}.obj').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (path/f'{name}.mtl').write_text('\n'.join(f'newmtl hc1_{key}\nKd 1 1 1\nmap_Kd ../textures/hc1_attachment_atlas_color.png\n' for key in sorted(used)),encoding='utf-8')
    remaps='\n'.join(f'{{ from = "hc1_{key}.vmat" to = "attachments/hc1/materials/hc1_{key}.vmat" }},' for key in sorted(used))
    (path/f'{name}.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
 rootNode = {
  _class = "RootNode"
  children = [
   { _class = "MaterialGroupList" children = [
    { _class = "DefaultMaterialGroup" remaps = [
'''+remaps+'''
     ] use_global_default = false }
   ] },
   { _class = "RenderMeshList" children = [
    { _class = "RenderMeshFile"
'''+f'     filename = "attachments/hc1/{name}/{name}.obj"\n'+'''
     import_translation = [ 0.0, 0.0, 0.0 ]
     import_rotation = [ 0.0, 0.0, 0.0 ]
     import_scale = 1.0
     align_origin_x_type = "None"
     align_origin_y_type = "None"
     align_origin_z_type = "None"
    }
   ] }
  ]
 }
}
''',encoding='utf-8')
    return {'triangles':tri_count,'components':len(objects),'materials':sorted(used),
            'bounds_min':[min(v[i] for v in bounds) for i in range(3)],
            'bounds_max':[max(v[i] for v in bounds) for i in range(3)]}


stats={}
for name, make in [('rifle_suppressor',lambda:suppressor(False)),
                   ('compact_suppressor',lambda:suppressor(True)),
                   ('vertical_grip',vertical_grip),('angled_grip',angled_grip)]:
    active_objects=[]
    make()
    bpy.context.view_layer.update()
    prepare_objects(active_objects)
    bpy.context.view_layer.update()
    parts[name]=active_objects.copy()
    stats[name]=export_obj(name,active_objects)

# Keep a source file with all four assets separated into named collections,
# at their export origins, and with the original generated atlas packed inside.
for name, objects in parts.items():
    collection=bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
image.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'hc1_attachments.blend'))
(QA/'mesh-report.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf-8')
if '--skip-render' in sys.argv:
    print('HC1_MESH_REPORT',json.dumps(stats))
    sys.exit(0)

# Render actual exported geometry, with no generated product image substituting for it.
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1800
scene.render.resolution_y=1400
scene.render.resolution_percentage=100
scene.world.color=(0.14,0.14,0.14)
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def light(name,loc,energy,size,target):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy
    data.shape='DISK'
    data.size=size
    obj=bpy.data.objects.new(name,data)
    scene.collection.objects.link(obj)
    obj.location=loc
    aim(obj,target)


positions={'rifle_suppressor':(-4.7,2.6,1.0),'compact_suppressor':(-3.8,-0.9,1.0),
           'vertical_grip':(4.2,2.0,4.2),'angled_grip':(4.6,-2.3,2.05)}
for name,objects in parts.items():
    for obj in objects:
        obj.location+=Vector(positions[name])
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0))
plane=bpy.context.object
mat=bpy.data.materials.new('Studio graphite')
mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(0.055,0.063,0.074,1)
bsdf.inputs['Roughness'].default_value=0.85
plane.data.materials.append(mat)
light('Large key',(-3,-9,14),2200,8,(0,0,0))
light('Rim strip',(3,7,11),2600,6,(0,0,1))
light('Front fill',(9,-3,8),1600,7,(0,0,1))
bpy.ops.object.camera_add(location=(14,-22,21))
camera=bpy.context.object
aim(camera,(0.5,0,1.1))
camera.data.type='ORTHO'
camera.data.ortho_scale=15.8
scene.camera=camera
scene.render.filepath=str(QA/'attachment-lineup.png')
bpy.ops.render.render(write_still=True)
print('HC1_MESH_REPORT',json.dumps(stats))
