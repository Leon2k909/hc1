"""Cosmetic game meshes in each rifle's bind space. Blender 5.1; no physical fabrication data."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Assets/attachments/rear_mag'
SRC=ROOT/'Sources/RearMagazine'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version=0
atlas=bpy.data.images.load(str(OUT/'textures/rear_mag_atlas_color.png'))
surfaces={'polymer':((0,.5),0,.70),'rubber':((.5,.5),0,.88),'tape':((0,0),0,.94),'metal':((.5,0),.85,.44),'recess':((.5,.5),0,.96)}
mats={}
for key,(_,metal,rough) in surfaces.items():
    mat=bpy.data.materials.new(key);mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Metallic'].default_value=metal;bsdf.inputs['Roughness'].default_value=rough
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=atlas
    mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
    mats[key]=mat
objects=[]
def finish(obj,name,surface,bevel=.04):
    obj.name=name;obj['surface']=surface;obj.data.materials.append(mats[surface]);objects.append(obj)
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Soft edges','BEVEL');mod.width=bevel;mod.segments=3
    for poly in obj.data.polygons:poly.use_smooth=True
    mod=obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    return obj
def box(name,loc,size,surface='polymer',bevel=.035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=size
    return finish(o,name,surface,bevel)
def profile(name,outline,width,cy,surface='rubber',bevel=.06):
    n=len(outline);verts=[(x,cy+y,z) for y in [-width/2,width/2] for x,z in outline]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    return finish(obj,name,surface,bevel)
def cylinder(name,loc,radius,depth,surface='metal',axis='Y',sides=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=sides,radius=radius,depth=depth,location=loc)
    o=bpy.context.object
    if axis=='Y':o.rotation_euler.x=math.pi/2
    return finish(o,name,surface,.008)

def grip(weapon,taped):
    if weapon=='m4a1':
        outline=[(-3.09,5.07),(-1.62,4.47),(-1.83,3.57),(-2.12,3.24),(-2.90,1.56),(-3.12,1.49),(-5.25,2.16),(-5.28,2.33)]
        cy=.001;width=1.32;top=4.75;bottom=1.88
        rear=lambda z:-5.25+(z-2.16)*.755
        front=lambda z:-2.97+(z-1.58)*.47
    else:
        outline=[(5.69,-5.50),(7.04,-6.01),(5.80,-8.86),(5.51,-8.93),(3.73,-8.35),(3.70,-8.08)]
        cy=-2.919;width=1.39;top=-5.88;bottom=-8.57
        rear=lambda z:3.76+(z+8.30)*.78
        front=lambda z:5.78+(z+8.84)*.445
    profile('ergonomic_overmold',outline,width,cy,'polymer' if taped else 'rubber',.10)
    # Authored raised side pads and actual wrap strips retain a clean seam at each edge.
    for i in range(7 if taped else 5):
        z=bottom+(top-bottom)*(i+.5)/(7 if taped else 5)
        h=.36 if taped else .13
        left=rear(z)+.11;right=front(z)-.10
        strip=[(left,z-h/2),(right,z-h/2-.10),(right+.06,z+h/2-.10),(left+.10,z+h/2)]
        if taped:
            profile('cloth_wrap_'+str(i),strip,width+.045,cy,'tape',.026)
        else:
            for side in [-1,1]:profile('traction_ridge_'+str(i),strip,.07,cy+side*width*.495,'rubber',.025)
    # Visible heel insert and inset retaining screw are purely cosmetic details.
    z=bottom-.12;x=(rear(z)+front(z))/2
    cap=box('heel_cap',(x,cy,z),(1.80,width+.015,.15),'polymer',.05)
    cap.rotation_euler.y=.32 if weapon=='m4a1' else .30

def magazine(weapon,extended):
    cy=.035 if weapon=='m4a1' else -2.917
    top=7.12 if weapon=='m4a1' else -4.18
    base_x=2.07 if weapon=='m4a1' else 10.32
    length=(8.55 if extended else 4.65) if weapon=='m4a1' else (7.65 if extended else 3.80)
    halfx=1.19 if weapon=='m4a1' else 1.29
    halfy=.545 if weapon=='m4a1' else .47
    def center(depth):return base_x+.014*depth*depth
    cross=[(-1,-.65),(-.86,-1),(.86,-1),(1,-.65),(1,.65),(.86,1),(-.86,1),(-1,.65)]
    rings=10;verts=[]
    for i in range(rings):
        depth=length*i/(rings-1)
        neck=max(0,min(1,(depth-1.35)/.85))
        hx=halfx*(.91+.09*neck);hy=halfy*(.78+.22*neck)
        verts.extend((center(depth)+x*hx,cy+y*hy,top-depth) for x,y in cross)
    faces=[tuple(reversed(range(8))),tuple(range((rings-1)*8,rings*8))]
    for r in range(rings-1):
        for i in range(8):j=(i+1)%8;faces.append((r*8+i,r*8+j,(r+1)*8+j,(r+1)*8+i))
    mesh=bpy.data.meshes.new('magazine_shell');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new('magazine_shell',mesh);bpy.context.collection.objects.link(obj);finish(obj,'magazine_shell','polymer',.045)
    # Reinforcement ribs run along the curved shell rather than floating over its bow.
    for side in [-1,1]:
        for rib in [-.72,0,.72]:
            a=[];b=[]
            for i in range(8):
                begin=1.4 if weapon=='m4a1' else 2.25
                dep=begin+(length-begin-.50)*i/7
                a.append((center(dep)+rib-.065,top-dep));b.append((center(dep)+rib+.065,top-dep))
            profile('molded_flute',a+list(reversed(b)),.095,cy+side*(halfy+.012),'polymer',.024)
        for i in range(3 if not extended else 6):
            dep=(1.65 if weapon=='m4a1' else 2.6)+i*.88
            if dep>length-.65:break
            cylinder('witness_recess',(center(dep)+.39,cy+side*(halfy+.018),top-dep),.062,.025,'recess',sides=16)
    box('reinforced_baseplate',(center(length),cy,top-length+.025),(halfx*2+.24,halfy*2+.23,.30),'rubber',.085)
    box('heel_latch',(center(length)+halfx+.08,cy,top-length+.04),(.15,.42,.12),'polymer',.035)
    for side in [-1,1]:box('feed_lip',(base_x,cy+side*halfy*.78,top+.04),(halfx*1.72,.11,.11),'metal',.025)
    for i in range(3):box('base_traction',(center(length)-.65+i*.63,cy,top-length-.145),(.20,halfy*1.75,.045),'rubber',.015)

def export(name,members,scale=1,shift=(0,0,0)):
    folder=OUT/name;folder.mkdir(parents=True,exist_ok=True)
    lines=[f'# RAZED {name} game art',f'mtllib {name}.mtl'];used=set();idx=1;points=[];triangles=0
    for obj in members:
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
        bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));tiny=[f for f in bm.faces if f.calc_area()<1e-8]
        if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES')
        bm.to_mesh(obj.data);bm.free()
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.1,island_margin=.02);bpy.ops.object.mode_set(mode='OBJECT')
        off=surfaces[obj['surface']][0]
        for uv in obj.data.uv_layers.active.data:uv.uv=(off[0]+.015+uv.uv.x*.47,off[1]+.015+uv.uv.y*.47)
        mesh=obj.data;mesh.calc_loop_triangles();normals=mesh.corner_normals;uvs=mesh.uv_layers.active.data
        surface=obj['surface'];used.add(surface);lines.extend([f'o {obj.name}',f'usemtl rm_{surface}'])
        for tri in mesh.loop_triangles:
            exported=[Vector(tuple(round(float(x),6) for x in (obj.matrix_world@mesh.vertices[mesh.loops[li].vertex_index].co)*scale+Vector(shift))) for li in tri.loops]
            if (exported[1]-exported[0]).cross(exported[2]-exported[0]).length_squared <= 1e-16:continue
            triangles+=1
            for li,v in zip(tri.loops,exported):
                n=(obj.matrix_world.to_3x3()@normals[li].vector).normalized();uv=uvs[li].uv;points.append(tuple(v))
                lines.extend([f'v {v.y:.6f} {v.z:.6f} {v.x:.6f}',f'vt {uv.x:.6f} {uv.y:.6f}',f'vn {n.y:.6f} {n.z:.6f} {n.x:.6f}'])
            lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(idx,idx+3)));idx+=3
    (folder/f'{name}.obj').write_text('\n'.join(lines)+'\n')
    (folder/f'{name}.mtl').write_text('\n'.join(f'newmtl rm_{s}\nKd 1 1 1\n' for s in sorted(used)))
    remaps='\n'.join('{ from = "rm_'+s+'.vmat" to = "attachments/rear_mag/materials/'+s+'.vmat" },' for s in sorted(used))
    (folder/f'{name}.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [
'''+remaps+'''
] use_global_default = false } ] },
{ _class = "RenderMeshList" children = [ { _class = "RenderMeshFile"
'''+f'filename = "attachments/rear_mag/{name}/{name}.obj"\n'+'''
import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1
align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None"
} ] } ] } }
''')
    return {'triangles':triangles,'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}

(OUT/'materials').mkdir(exist_ok=True)
for key,(_,metal,rough) in surfaces.items():
    tint=.28 if key in ['polymer','rubber'] else (.10 if key=='recess' else .55)
    (OUT/'materials'/f'{key}.vmat').write_text('''"Layer0"
{
shader "shaders/complex.shader"
F_SPECULAR "1"
F_METALNESS_TEXTURE "0"
'''+f'g_flMetalness "{metal}"\ng_flRoughnessScaleFactor "{rough}"\n'+'''
TextureColor "attachments/rear_mag/textures/rear_mag_atlas_color.png"
TextureNormal "materials/default/default_normal.tga"
TextureRoughness "materials/default/default_rough.tga"
TextureAmbientOcclusion "materials/default/default_ao.tga"
'''+f'g_vColorTint "[{tint} {tint} {tint} 1]"\n'+'''
g_flModelTintAmount "1"
}
''')
report={}
for weapon in ['m4a1','scarh']:
    for key in ['rubber_grip','taped_grip','short_mag','extended_mag']:
        objects=[]
        if 'grip' in key:grip(weapon,key=='taped_grip')
        else:magazine(weapon,key=='extended_mag')
        bpy.context.view_layer.update();name=weapon+'_'+key
        report[name]=export(name,objects)
        if weapon=='scarh':report[name+'_world']=export(name+'_world',objects,1.4,(-9.1,4.9,7.0))
        collection=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(collection)
        for obj in objects:
            for old in list(obj.users_collection):old.objects.unlink(obj)
            collection.objects.link(obj)
atlas.pack();bpy.ops.wm.save_as_mainfile(filepath=str(SRC/'rear_mag_parts.blend'))
(SRC/'qa/mesh-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
