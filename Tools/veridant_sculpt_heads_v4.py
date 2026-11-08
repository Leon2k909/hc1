"""Build an editable, UV-unwrapped lion head and swept mane replacement in Blender."""
import bpy, math
from mathutils import Vector
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=R/'Assets/models/props/shared/veridant_fountain_reference_top_v4'
D.mkdir(parents=True,exist_ok=True)
scene=bpy.data.scenes.new('Veridant sculpted heads v4')
bpy.context.window.scene=scene
bronze=bpy.data.materials.new('sculpt_bronze')
dark=bpy.data.materials.new('sculpt_recess')
parts=[]
def sphere(name,loc,scale,mat=bronze):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    return o
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def union(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    o=bpy.context.object;o.name=name
    m=o.modifiers.new('Continuous cast surface','REMESH');m.mode='VOXEL';m.voxel_size=.14
    bpy.ops.object.modifier_apply(modifier=m.name)
    m=o.modifiers.new('Sculpt surface relaxation','SMOOTH');m.factor=.5;m.iterations=4
    bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons:p.use_smooth=True
    return o
def subtract(o,loc,scale):
    cut=sphere('socket tool',loc,scale);active(o)
    m=o.modifiers.new('Recess','BOOLEAN');m.operation='DIFFERENCE';m.object=cut
    bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cut,do_unlink=True)
def lock(name,points,width,depth):
    # Cubic swept, pointed locks with a raised centre and fine longitudinal ridges.
    pts=[Vector(p) for p in points];verts=[];faces=[];n=24;k=12
    for i in range(n+1):
        t=i/n;u=1-t
        c=u**3*pts[0]+3*u*u*t*pts[1]+3*u*t*t*pts[2]+t**3*pts[3]
        tangent=(3*u*u*(pts[1]-pts[0])+6*u*t*(pts[2]-pts[1])+3*t*t*(pts[3]-pts[2])).normalized()
        normal=Vector((.2,c.y/6,.3)).normalized();across=tangent.cross(normal).normalized();normal=across.cross(tangent).normalized()
        taper=(.50+.50*math.sin(math.pi*min(t/.65,1)))*(1-t)**.65+.015
        for j in range(k):
            a=j*2*math.pi/k
            ridge=1+.12*math.cos(a*3+t*2)
            verts.append(c+across*(math.cos(a)*width*taper)+normal*(math.sin(a)*depth*taper*ridge))
        if i<n:
            for j in range(k):
                a=i*k+j;b=i*k+(j+1)%k;faces.append((a,b,b+k,a+k))
    faces.extend([tuple(range(k-1,-1,-1)),tuple(n*k+j for j in range(k))])
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    o=bpy.data.objects.new(name,mesh);scene.collection.objects.link(o);o.data.materials.append(bronze)
    for p in mesh.polygons:p.use_smooth=True
    return o
skin=union([
    sphere('skull',(23,0,74),(4.5,4.2,5.0)),
    sphere('forehead',(25,0,76),(3.0,3.9,2.6)),
    sphere('nasal bridge',(27,0,73.9),(3.0,1.85,2.2)),
    sphere('muzzle left',(28.5,1.5,71.7),(2.7,1.65,1.65)),
    sphere('muzzle right',(28.5,-1.5,71.7),(2.7,1.65,1.65)),
    sphere('jaw',(26.8,0,68.8),(3.6,2.65,1.5)),
    sphere('neck',(20.8,0,66.5),(4.4,4.4,6.1)),
    sphere('brow left',(26.6,2.7,75.5),(2.0,1.2,.8)),
    sphere('brow right',(26.6,-2.7,75.5),(2.0,1.2,.8)),
], 'Sculpted continuous lion head')
subtract(skin,(29.8,0,69.8),(3.6,2.0,.88))
for s in (-1,1):
    subtract(skin,(27,s*3.15,74.4),(1.15,.8,.75))
    parts.append(sphere('Inset bronze eye',(26.95,s*3.12,74.4),(.65,.58,.48),dark))
    ear=sphere('Rounded ear',(22.0,s*4.0,78.3),(1.1,1.25,1.65))
    subtract(ear,(22.65,s*4.1,78.5),(.85,.85,1.1));parts.append(ear)
    parts.append(sphere('Upper canine',(29.5,s*1.35,69.65),(.28,.28,.65)))
parts.append(skin)
nose=sphere('Broad nose leather',(30.6,0,72.8),(.75,1.65,.9),dark)
for s in (-1,1):subtract(nose,(31.2,s*.95,72.5),(.35,.45,.3))
parts.append(nose)
for s in (-1,1):
    for row in range(3):
        for i in range(9):
            a=i/8
            x=24.7-row*1.8-a*1.2;y=s*(3.3+row*.65+math.sin(a*math.pi)*1.3);z=78.3-a*14.5
            parts.append(lock('Layered swept mane',[(x,y,z),(x-2,y+s*.9,z+.1),(x-3.2,y+s*.8,z-2.1),(x-4.1,y-s*.2,z-3.6)],1.05-row*.12,.43))
    for i in range(6):
        y=s*(.6+i*.65)
        parts.append(lock('Crown swept lock',[(26-i*.4,y,78.0),(24,y+s*.3,80.1),(21,y+s*.5,80.3),(18.4,y+s*.3,78.0)],.66,.4))
    for i in range(5):
        parts.append(lock('Chest cascade',[(25.3,s*(1+i*.65),68),(25.5,s*(1.5+i*.7),65),(23.8,s*(2+i*.6),62),(21.4,s*(1.7+i*.5),60.3)],.85,.4))
# UV islands for every new modeled surface, then pack the complete head together.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=skin;bpy.ops.object.join();head=bpy.context.object
head.name='Lion head and mane UV master'
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(58),island_margin=.015)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.wm.save_as_mainfile(filepath=str(D/'heads.blend'))
# Preserve original lower sculpture and stone pier with their source UVs.
lines=(R/'Assets/models/props/shared/veridant_fountain_reference_top_v2/crown.obj').read_text().splitlines()
positions=[];out=[];mat='';removed=0
for line in lines:
    if line.startswith('v '):
        y,z,x=map(float,line.split()[1:]);positions.append((.6*x-.8*y,.8*x+.6*y,z))
    if line.startswith('usemtl '):mat=line.split()[1]
    if line.startswith('f ') and mat=='crown_surface':
        coords=[positions[int(p.split('/')[0])-1] for p in line.split()[1:]]
        if any(abs(p[0])>13 and p[2]>61.5 for p in coords):removed+=1;continue
    out.append(line)
nv=len(positions);nt=sum(l.startswith('vt ') for l in out);nn=sum(l.startswith('vn ') for l in out)
mesh=head.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active.data
for sign in (-1,1):
    for tri in mesh.loop_triangles:
        material=head.material_slots[tri.material_index].material.name
        out.append('usemtl sculpt_recess' if material.startswith('sculpt_recess') else 'usemtl sculpt_bronze')
        ids=[]
        for li in tri.loops:
            loop=mesh.loops[li];v=head.matrix_world@mesh.vertices[loop.vertex_index].co
            n=head.matrix_world.to_3x3()@mesh.vertices[loop.vertex_index].normal
            x,y,z=v;x*=sign;y*=sign
            wx=.6*x+.8*y;wy=-.8*x+.6*y
            nx,ny,nz=n;nx*=sign;ny*=sign
            out.extend([f'v {wy} {z} {wx}',f'vt {uv[li].uv.x} {uv[li].uv.y}',f'vn {-.8*nx+.6*ny} {nz} {.6*nx+.8*ny}'])
            nv+=1;nt+=1;nn+=1;ids.append(f'{nv}/{nt}/{nn}')
        out.append('f '+' '.join(ids))
(D/'crown.obj').write_text('\n'.join(out))
(D/'crown.mtl').write_text('newmtl crown_surface\nnewmtl crown_stone\nnewmtl sculpt_bronze\nnewmtl sculpt_recess\n')
t=(R/'Assets/models/props/shared/veridant_fountain_reference_top_v2/crown.vmdl').read_text().replace('veridant_fountain_reference_top_v2/crown.obj','veridant_fountain_reference_top_v4/crown.obj')
t=t.replace('remaps =','remaps =').replace('{ from = "crown_surface.vmat"', '{ from = "sculpt_bronze.vmat" to = "materials/veridant/fountain_reference_bronze.vmat" },\n{ from = "sculpt_recess.vmat" to = "materials/veridant/fountain_reference_bronze.vmat" },\n{ from = "crown_surface.vmat"')
(D/'crown.vmdl').write_text(t)
print('Sculpted triangles',len(mesh.loop_triangles),'replaced faces',removed,'UV loops',len(uv))
import runpy
runpy.run_path(str(R/'Tools/veridant_pack_sculpt_obj.py'))
