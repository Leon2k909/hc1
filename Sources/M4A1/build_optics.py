"""Author a cosmetic enclosed red-dot optic; no functional weapon internals."""
import bpy,bmesh,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Assets/attachments/m4a1/tube_red_dot';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.context.preferences.filepaths.save_version=0
collection=bpy.data.collections.new('tube_red_dot');bpy.context.scene.collection.children.link(collection)
materials={}
for name in ['anodized','steel','rubber']:
    mat=bpy.data.materials.new('hc1_'+name);mat.use_nodes=True;materials[name]=mat
def finish(obj,name,surface='anodized',bevel=.02):
    obj.name=name;obj.data.materials.append(materials[surface]);obj['surface']=surface
    for old in list(obj.users_collection):old.objects.unlink(obj)
    collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=obj.modifiers.new('Machined edge','BEVEL');mod.width=bevel;mod.segments=3
    mod=obj.modifiers.new('Weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    for poly in obj.data.polygons:poly.use_smooth=True
    return obj
def box(name,loc,size,surface='anodized',bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=size
    return finish(o,name,surface,bevel)
def cylinder(name,loc,radius,depth,axis='Z',surface='anodized'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=radius,depth=depth,location=loc);o=bpy.context.object
    if axis=='X':o.rotation_euler.y=math.pi/2
    if axis=='Y':o.rotation_euler.x=math.pi/2
    return finish(o,name,surface,.015)
def ring(name,x,length,radius,inner,surface='anodized'):
    n=64;verts=[(xx,r*math.cos(i*math.tau/n),1.44+r*math.sin(i*math.tau/n)) for xx,r in [(x,radius),(x+length,radius),(x+length,inner),(x,inner)] for i in range(n)]
    faces=[(row*n+i,row*n+(i+1)%n,((row+1)%4)*n+(i+1)%n,((row+1)%4)*n+i) for row in range(4) for i in range(n)]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);return finish(o,name,surface,.018)
box('rail_clamp',(0,0,.16),(1.92,1.1,.32))
box('raised_mount',(0,0,.48),(1.15,.7,.4))
box('mount_saddle',(0,0,.71),(1.52,1.01,.22))
ring('optic_body',-1.24,2.48,.74,.60)
ring('rear_rim',-1.40,.24,.80,.62)
ring('front_rim',1.12,.30,.79,.63)
ring('front_rubber_seal',1.33,.09,.76,.65,'rubber')
ring('rear_rubber_seal',-1.43,.07,.76,.63,'rubber')
for x in [-.95,.7]:ring('body_seam',x,.04,.75,.70,'steel')
cylinder('elevation_turret',(.05,0,2.19),.32,.28)
cylinder('windage_turret',(.1,-.73,1.44),.31,.33,'Y')
cylinder('brightness_dial',(-.28,.78,1.44),.40,.33,'Y')
for i in range(20):
    angle=math.tau*i/20
    o=box('dial_knurl',(-.28+.39*math.cos(angle),.80,1.44+.39*math.sin(angle)),(.045,.26,.055),'rubber',.009);o.rotation_euler.y=-angle
for x in [-.61,.61]:
    cylinder('rail_crossbolt',(x,-.58,.20),.12,.14,'Y','steel')
    box('socket_slot',(x,-.66,.20),(.13,.015,.025),'rubber',.004)
for o in list(collection.objects):
    bpy.context.view_layer.objects.active=o
    for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Sources/M4A1/m4a1_optics.blend'))
# A separate lens draw call retains clear glass when the housing is painted.
lines=['mtllib tube_lens.mtl','o tube_lens','usemtl optic_reticle']
n=64;verts=[(-1.30,0,1.44)]+[(-1.30,.61*math.cos(i*math.tau/n),1.44+.61*math.sin(i*math.tau/n)) for i in range(n)]
for x,y,z in verts:lines.extend([f'v {y} {z} {x}',f'vt {y/1.22+.5} {(z-1.44)/1.22+.5}','vn 0 0 -1'])
for i in range(n):lines.append('f '+' '.join(f'{j}/{j}/{j}' for j in [1,(i+1)%n+2,i+2]))
(OUT/'tube_lens.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
(OUT/'tube_lens.mtl').write_text('newmtl optic_reticle\nKd 1 1 1\n',encoding='utf8')
print('Patrol optic authored')
