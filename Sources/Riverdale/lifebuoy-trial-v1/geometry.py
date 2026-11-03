"""Small deterministic Blender mesh helpers; coordinates in inches, output metres."""
import math
import bpy,bmesh
from mathutils import Vector
S=.0254
parts=[]

def mesh(name,vs,fs,mat,smooth=False,uv=None,fix=True):
    data=bpy.data.meshes.new(name);data.from_pydata([tuple(c*S for c in p) for p in vs],[],fs);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);data.materials.append(mat)
    if fix:
        bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
    layer=data.uv_layers.new(name='UVMap')
    for p in data.polygons:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(p.normal[i]))]
        p.use_smooth=smooth and len(p.vertices)<=4
        for li in p.loop_indices:
            vi=data.loops[li].vertex_index
            layer.data[li].uv=uv[vi] if uv else (vs[vi][axes[0]]/48,vs[vi][axes[1]]/48)
    parts.append(obj);return obj

def bevel(o,width=.08,segments=3):
    bpy.context.view_layer.objects.active=o
    m=o.modifiers.new('Manufactured edge radii','BEVEL');m.width=width*S;m.segments=segments;m.limit_method='ANGLE';m.harden_normals=True
    bpy.ops.object.modifier_apply(modifier=m.name)
    m=o.modifiers.new('Preserve planar faces','WEIGHTED_NORMAL');m.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=m.name);return o

def box(name,p,size,mat,r=.08):
    bpy.ops.mesh.primitive_cube_add(size=1,location=tuple(v*S for v in p));o=bpy.context.object;o.name=name
    o.dimensions=tuple(v*S for v in size);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat)
    if r:bevel(o,min(r,min(size)*.40))
    parts.append(o);return o

def rr(w,h,r,steps=6):
    out=[]
    for cx,cz,a0 in [(w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)]:
        for i in range(steps+1):
            a=math.radians(a0+90*i/steps);out.append((cx+r*math.cos(a),cz+r*math.sin(a)))
    return out

def frame(name,depths,outer,inner,mat):
    a=rr(*outer);b=rr(*inner);n=len(a);vs=[(x,-d,z) for d in depths for ring in (a,b) for x,z in ring];fs=[]
    for i in range(n):
        j=(i+1)%n
        fs.extend([(i,j,n+j,n+i),(2*n+i,3*n+i,3*n+j,2*n+j),(i,2*n+i,2*n+j,j),(n+i,n+j,3*n+j,3*n+i)])
    return bevel(mesh(name,vs,fs,mat),.045)

def tube(name,points,r,mat,sides=10):
    points=[Vector(p) for p in points];vs=[]
    first=(points[1]-points[0]).normalized()
    index=min(range(3),key=lambda i:abs(first[i]));basis=Vector(tuple(1 if i==index else 0 for i in range(3)))
    for i,p in enumerate(points):
        tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        a=basis-tangent*basis.dot(tangent)
        if a.length<1e-5:
            index=min(range(3),key=lambda k:abs(tangent[k]));ref=Vector(tuple(1 if k==index else 0 for k in range(3)))
            a=ref-tangent*ref.dot(tangent)
        a.normalize();basis=a;b=tangent.cross(a)
        for k in range(sides):vs.append(tuple(p+r*(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))))
    fs=[tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))]
    for i in range(len(points)-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    return mesh(name,vs,fs,mat,True)

def turn(name,p,axis,profile,mat,sides=24):
    p=Vector(p);axis=Vector(axis).normalized();ref=Vector((0,0,1)) if abs(axis.z)<.9 else Vector((1,0,0))
    a=axis.cross(ref).normalized();b=axis.cross(a);vs=[]
    for radius,depth in profile:
        for k in range(sides):vs.append(tuple(p+axis*depth+radius*(a*math.cos(k*math.tau/sides)+b*math.sin(k*math.tau/sides))))
    fs=[]
    for k in range(len(profile)-1):
        for i in range(sides):j=(i+1)%sides;fs.append((k*sides+i,k*sides+j,(k+1)*sides+j,(k+1)*sides+i))
    fs.extend([tuple(reversed(range(sides))),tuple(range(len(vs)-sides,len(vs)))])
    return mesh(name,vs,fs,mat,True)

def transform(o,center,axes):
    center=Vector(center)*S;axes=[Vector(a) for a in axes]
    # Mesh helpers use applied locations except box; preserve both paths.
    world=o.matrix_world.copy()
    for v in o.data.vertices:
        p=world@v.co;v.co=center+sum((axes[i]*p[i] for i in range(3)),Vector())
    o.matrix_world.identity();o.data.update();return o
