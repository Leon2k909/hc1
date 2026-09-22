"""Build two cosmetic M4A1 game meshes with Blender 5.x; +X forward, +Z up.

Uses a dedicated Recon metal texture and the HC1 stock atlas. Exports only this pack's files.
"""
import bpy, bmesh, math, json, shutil
from mathutils import Matrix
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Assets/attachments/m4a1'
SOURCE = ROOT / 'Sources/M4A1'
ATLAS = ROOT / 'Assets/attachments/hc1/textures/hc1_attachment_atlas_color.png'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version = 0
tex = bpy.data.images.load(str(ATLAS))
guard_tex = bpy.data.images.load(str(OUT/'textures/recon_anodized_color.png'))
surfaces = {'polymer': ((.5,.5), 0,.78), 'anodized': ((0,.5), .78,.46), 'steel': ((0,0), .94,.32), 'recess': ((0,0),0,.95), 'guard': ((0,0),.65,.52), 'stock': ((0,0),0,.78)}
materials = {}
for name, (uv, metal, rough) in surfaces.items():
    mat = bpy.data.materials.new('hc1_'+name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = rough
    image = mat.node_tree.nodes.new('ShaderNodeTexImage')
    image.image = guard_tex if name in ('guard','recess','stock') else tex
    mat.node_tree.links.new(image.outputs['Color'], shader.inputs['Base Color'])
    if name=='recess':
        mat.node_tree.links.remove(shader.inputs['Base Color'].links[0])
        shader.inputs['Base Color'].default_value=(.004,.004,.004,1)
    materials[name] = mat

objects = []
def finish(obj, name, surface, bevel=.035):
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(materials[surface])
    obj['surface'] = surface
    for face in obj.data.polygons: face.use_smooth=True
    if bevel:
        mod = obj.modifiers.new('Edge bevel', 'BEVEL'); mod.width=bevel; mod.segments=2
    mod = obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL'); mod.keep_sharp=True
    objects.append(obj)
    return obj

def box(name, loc, size, surface='polymer', bevel=.045):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj=bpy.context.object; obj.dimensions=size
    return finish(obj,name,surface,bevel)

def cylinder(name, loc, radius, depth, surface='steel', axis='Y', vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    obj=bpy.context.object
    if axis=='X': obj.rotation_euler.y=math.pi/2
    if axis=='Y': obj.rotation_euler.x=math.pi/2
    return finish(obj,name,surface,.012)

def profile(name, outline, halfwidth, surface='polymer'):
    n=len(outline)
    verts=[(x,y,z) for y in [-halfwidth,halfwidth] for x,z in outline]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(mesh); bm.free()
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    return finish(obj,name,surface,.075)

def sleeve(name, points, surface='anodized', sides=48):
    verts=[(x,r*math.cos(i*math.tau/sides),r*math.sin(i*math.tau/sides)) for x,r in points for i in range(sides)]
    faces=[]
    for row in range(len(points)):
        nxt=(row+1)%len(points)
        for i in range(sides):
            j=(i+1)%sides
            faces.append((row*sides+i,row*sides+j,nxt*sides+j,nxt*sides+i))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.update()
    bm=bmesh.new(); bm.from_mesh(mesh); bmesh.ops.recalc_face_normals(bm,faces=bm.faces); bm.to_mesh(mesh); bm.free()
    for f in mesh.polygons: f.use_smooth=True
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    return finish(obj,name,surface,.008)

def stock():
    # Complete replacement: buffer connector, open-frame stock, lever, buttplate.
    cylinder('buffer_connector',(.35,0,0),.46,3.7,'guard',axis='X',vertices=40)
    shell=profile('stock_chassis',[(-5.52,.65),(-1.05,.65),(.65,.10),(.65,-.55),(-1.2,-1.05),(-4.05,-3.0),(-5.65,-3.0)],.73,'stock')
    cutter=profile('temporary_window',[(-4.87,-.68),(-1.70,-.68),(-4.22,-2.37),(-4.87,-2.37)],1.5,'stock')
    bpy.context.view_layer.objects.active=cutter
    for mod in list(cutter.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.context.view_layer.objects.active=shell
    # Cut before the chassis edge bevel so the opening gets the same finish.
    mod=shell.modifiers.new('Open frame','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
    bpy.ops.object.modifier_move_to_index(modifier=mod.name,index=0)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    objects.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
    profile('integrated_cheek',[(-5.40,.64),(-5.18,.92),(-1.55,.92),(-.85,.48),(-1.00,.10),(-5.38,.10)],.88,'stock')
    profile('buttplate_frame',[(-5.64,.82),(-5.38,.78),(-5.48,-3.08),(-5.78,-3.12)],.79,'guard')
    profile('rubber_buttpad',[(-5.96,.75),(-5.67,.84),(-5.77,-3.14),(-6.05,-3.02)],.85,'recess')
    for i in range(11):
        box('buttpad_traction',(-6.02,0,.55-i*.31),(.065,1.59,.065),'recess',.018)
    lever=box('adjustment_lever',(-.85,0,-1.04),(1.95,.85,.23),'guard',.085)
    lever.rotation_euler.y=-.16
    cylinder('lever_pivot',(-.14,0,-.73),.14,1.53,'guard',vertices=16)
    for side in [-1,1]:
        cylinder('sling_socket_rim',(-5.2,side*.755,-1.64),.23,.075,'guard',vertices=32)
        cylinder('sling_socket_recess',(-5.2,side*.801,-1.64),.15,.014,'recess',vertices=32)
        for x in [-4.86,-1.68]:
            cylinder('chassis_fastener',(x,side*.745,-.39),.10,.04,'guard',vertices=8)
        for i in range(5):
            box('cheek_detail',(-4.5+i*.49,side*.883,.28),(.23,.035,.055),'guard',.018)

def barrel():
    # A game-art barrel/handguard conversion, spanning receiver to gas block.
    # The slender original barrel and its muzzle remain exposed at the front.
    section=[(-.84,-1.15),(.84,-1.15),(1.16,-.80),(1.16,.70),
             (.83,1.12),(-.83,1.12),(-1.16,.70),(-1.16,-.80)]
    verts=[(x,y*s,z*s) for s in [1,.89] for x in [-13.2,-2.2] for y,z in section]
    faces=[]
    for i in range(8):
        j=(i+1)%8
        faces.extend([(i,j,8+j,8+i),(16+i,24+i,24+j,16+j),
                      (i,16+i,16+j,j),(8+i,8+j,24+j,24+i)])
    mesh=bpy.data.meshes.new('vented_handguard');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    guard=bpy.data.objects.new('vented_handguard',mesh);bpy.context.collection.objects.link(guard)
    # Actual slots in the outer shell; no solid suppressor-like cylinder.
    for z in [-.55,.35]:
        for i in range(7):
            bpy.ops.mesh.primitive_cube_add(size=1,location=(-11.35+i*1.30,0,z))
            cutter=bpy.context.object;cutter.dimensions=(.98,3.4,.28)
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
            bevel=cutter.modifiers.new('Rounded slot','BEVEL');bevel.width=.10;bevel.segments=3
            bpy.context.view_layer.objects.active=cutter;bpy.ops.object.modifier_apply(modifier=bevel.name)
            mod=guard.modifiers.new('Vent cutout','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
            bpy.context.view_layer.objects.active=guard;bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter,do_unlink=True)
    finish(guard,'vented_handguard','guard',.032)
    box('top_rail_spine',(-7.65,0,1.13),(11.05,.61,.18),'guard',.025)
    for i in range(24):
        box('top_rail_lug',(-12.98+i*.46,0,1.29),(.29,.87,.19),'guard',.025)
    box('lower_accessory_rail',(-8.75,0,-1.17),(6.0,.69,.16),'guard',.025)
    for i in range(14):
        box('lower_rail_lug',(-11.55+i*.43,0,-1.30),(.27,.85,.17),'guard',.02)
    for side in [-1,1]:
        box('rear_clamp',(-12.83,side*1.10,-.02),(.63,.23,1.42),'guard',.07)
        for z in [-.42,.42]:
            cylinder('clamp_fastener',(-12.83,side*1.235,z),.13,.06,'steel',vertices=8)
            cylinder('clamp_hex_socket',(-12.83,side*1.271,z),.061,.016,'recess',vertices=6)
        # Dark inner liner masks the baked world-model rail behind the vents.
        box('recessed_vent_liner',(-8.85,side*1.025,-.09),(6.55,.025,1.2),'recess',.01)

def export(name, members):
    folder=OUT/name; folder.mkdir(parents=True,exist_ok=True)
    lines=[f'# RAZED M4A1 {name}: game mesh',f'mtllib {name}.mtl']; index=1; count=0; bounds=[]; used=set()
    for obj in members:
        bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers): bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        bm=bmesh.new(); bm.from_mesh(obj.data); bmesh.ops.triangulate(bm,faces=list(bm.faces))
        tiny=[f for f in bm.faces if f.calc_area()<1e-7]
        if tiny: bmesh.ops.delete(bm,geom=tiny,context='FACES')
        bm.to_mesh(obj.data); bm.free()
        if obj['surface'] in ('guard','recess','stock'):
            # A fixed density in model space keeps grain continuous along the
            # handguard, instead of stretching a separate island per vent/rail.
            uv_layer=obj.data.uv_layers.active or obj.data.uv_layers.new(name='UVMap')
            for face in obj.data.polygons:
                normal=obj.matrix_world.to_3x3()@face.normal
                axis=max(range(3),key=lambda i:abs(normal[i]))
                axes=(1,2) if axis==0 else ((0,2) if axis==1 else (0,1))
                for li in face.loop_indices:
                    co=obj.matrix_world@obj.data.vertices[obj.data.loops[li].vertex_index].co
                    uv_layer.data[li].uv=(co[axes[0]]/6.0,co[axes[1]]/6.0)
        else:
            bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.025); bpy.ops.object.mode_set(mode='OBJECT')
            uv_offset=surfaces[obj['surface']][0]
            for loop in obj.data.uv_layers.active.data:
                loop.uv.x=uv_offset[0]+.02+loop.uv.x*.46; loop.uv.y=uv_offset[1]+.02+loop.uv.y*.46
        mesh=obj.data; mesh.calc_loop_triangles(); uvs=mesh.uv_layers.active.data; normals=mesh.corner_normals
        used.add(obj['surface']); lines.extend([f'o {obj.name}',f'usemtl hc1_{obj["surface"]}'])
        for triangle in mesh.loop_triangles:
            count+=1
            for li in triangle.loops:
                v=obj.matrix_world@mesh.vertices[mesh.loops[li].vertex_index].co
                n=(obj.matrix_world.to_3x3()@normals[li].vector).normalized(); uv=uvs[li].uv; bounds.append(tuple(v))
                # Counter the ModelDoc OBJ importer's (x,y,z)->(z,x,y) convention.
                lines.extend([f'v {v.y:.7f} {v.z:.7f} {v.x:.7f}',f'vt {uv.x:.7f} {uv.y:.7f}',f'vn {n.y:.7f} {n.z:.7f} {n.x:.7f}'])
            lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(index,index+3))); index+=3
    (folder/f'{name}.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
    (folder/f'{name}.mtl').write_text('\n'.join(f'newmtl hc1_{k}\nKd 1 1 1\n' for k in sorted(used)),encoding='utf8')
    special={'recess':'attachments/m4a1/materials/vent_recess.vmat','guard':'attachments/m4a1/materials/recon_anodized.vmat','stock':'attachments/m4a1/materials/recon_polymer.vmat'}
    remaps='\n'.join('{ from = "hc1_'+k+'.vmat" to = "'+special.get(k,'attachments/hc1/materials/hc1_'+k+'.vmat')+'" },' for k in sorted(used))
    (folder/f'{name}.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
 { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [
'''+remaps+'''
 ] use_global_default = false } ] },
 { _class = "RenderMeshList" children = [ { _class = "RenderMeshFile"
'''+f'filename = "attachments/m4a1/{name}/{name}.obj"\n'+'''
 import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1
 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
 } ] }
] } }
''',encoding='utf8')
    return {'triangles':count,'bounds_min':[min(v[i] for v in bounds) for i in range(3)],'bounds_max':[max(v[i] for v in bounds) for i in range(3)]}

stats={}
for name,make in [('precision_stock',stock),('heavy_barrel',barrel)]:
    objects=[]; make(); bpy.context.view_layer.update()
    scale=Matrix.Identity(4)
    for obj in objects: obj.matrix_world=scale@obj.matrix_world
    bpy.context.view_layer.update()
    stats[name]=export(name,objects)
    collection=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(collection)
    for obj in objects:
        for old in list(obj.users_collection): old.objects.unlink(obj)
        collection.objects.link(obj)
tex.pack()
guard_tex.pack()
# Write through a staging file; the editor may hold the old .blend open for indexing.
staging=SOURCE/'m4a1_parts_build.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(staging))
shutil.copyfile(staging,SOURCE/'m4a1_parts.blend')
staging.unlink()
(SOURCE/'mesh-report.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf8')
print('RAZED_M4_MESHES',json.dumps(stats))
