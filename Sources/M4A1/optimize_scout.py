"""Reduce the old scope source mesh for a weapon attachment; preserve UV islands."""
import bpy,bmesh,json,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];folder=ROOT/'Assets/attachments/m4a1/optics'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
vertices=[];uvs=[];faces=[];face_mats=[];mat_names=[];current=0
source=ROOT/'Sources/M4A1/scout_source.obj'
if not source.is_file():source=folder/'scout.obj'
for line in source.read_text().splitlines():
    f=line.split()
    if not f:continue
    if f[0]=='v':vertices.append(tuple(map(float,f[1:])))
    elif f[0]=='vt':uvs.append(tuple(map(float,f[1:])))
    elif f[0]=='usemtl':
        if f[1] not in mat_names:mat_names.append(f[1])
        current=mat_names.index(f[1])
    elif f[0]=='f':faces.append([int(x.split('/')[0])-1 for x in f[1:]]);face_mats.append(current)
mesh=bpy.data.meshes.new('scout');mesh.from_pydata(vertices,[],faces);mesh.update()
obj=bpy.data.objects.new('scout',mesh);bpy.context.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
uv=mesh.uv_layers.new(name='UVMap')
for name in mat_names:mesh.materials.append(bpy.data.materials.new(name))
for p,mat in zip(mesh.polygons,face_mats):
    p.material_index=mat;p.use_smooth=True
    for li in p.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.000001);bm.to_mesh(mesh);bm.free()
mod=obj.modifiers.new('Attachment polygon budget','DECIMATE');mod.ratio=.26;mod.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=mod.name)
# Remove opaque internal end caps without cutting the donor's outer tubes.
# OBJ Z is the optic's forward axis. Side walls retain their original surface.
bm=bmesh.new();bm.from_mesh(obj.data)
caps=[]
for face in bm.faces:
    center=face.calc_center_median();radius=math.hypot(center.x+.0425439,center.y-1.0682995)
    if abs(face.normal.z)>.7 and radius<.53:caps.append(face)
bmesh.ops.delete(bm,geom=caps,context='FACES');bm.to_mesh(obj.data);bm.free()
mesh=obj.data
bm=bmesh.new();bm.from_mesh(mesh)
for edge in bm.edges:
    if edge.is_manifold:edge.smooth=edge.calc_face_angle()<math.radians(35)
bm.to_mesh(mesh);bm.free()
weighted=obj.modifiers.new('Preserve machined flats','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=50
bpy.ops.object.modifier_apply(modifier=weighted.name)
mesh=obj.data
mat_names.append('optic_lens_baffle');mesh.materials.append(bpy.data.materials.new('optic_lens_baffle'))
for polygon in mesh.polygons:
    radial=polygon.center.copy();radial.x+=.0425439;radial.y-=1.0682995;radial.z=0
    if radial.length<1.15 and radial.length>0 and polygon.normal.dot(radial.normalized())<-.15:
        polygon.material_index=len(mat_names)-1
# Assign visible interior surfaces through the rear aperture to the black
# baffle material, including the donor's overlapping inner sleeve surfaces.
surfaces=[p for p in mesh.polygons if mat_names[p.material_index] not in ('material','material_002')]
tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[tuple(p.vertices) for p in surfaces])
eye=Vector((-.0425439,1.0682995,-8.4727))
interior_faces=set()
for row in range(129):
    for col in range(129):
        x=(col/128*2-1)*.447;y=(row/128*2-1)*.447
        if x*x+y*y>.447**2:continue
        origin=Vector((x-.0425439,y+1.0682995,-4.649))
        direction=(origin-eye).normalized()
        for _ in range(16):
            hit,normal,index,distance=tree.ray_cast(origin,direction,12)
            if index is None:break
            surfaces[index].material_index=mat_names.index('optic_lens_baffle')
            interior_faces.add(surfaces[index].index)
            origin=hit+direction*.0001
# Include subpixel slivers adjacent to the sampled surfaces so camo cannot
# leak between the baffles when the viewmodel sways slightly during ADS.
for _ in range(2):
    border_vertices={v for index in interior_faces for v in mesh.polygons[index].vertices}
    for polygon in surfaces:
        center=polygon.center;distance=center.z-eye.z
        projected=math.hypot(center.x-eye.x,center.y-eye.y)*3.8227/max(distance,.001)
        if center.z>-4.649 and projected<.48 and any(v in border_vertices for v in polygon.vertices):
            polygon.material_index=mat_names.index('optic_lens_baffle');interior_faces.add(polygon.index)
mesh=obj.data;mesh.calc_loop_triangles();normals=mesh.corner_normals;uv=mesh.uv_layers.active.data
lines=['mtllib scout.mtl','o scout'];index=1
for tri in mesh.loop_triangles:
    lines.append('usemtl '+mat_names[tri.material_index])
    for li in tri.loops:
        p=mesh.vertices[mesh.loops[li].vertex_index].co;n=normals[li].vector;t=uv[li].uv
        lines.extend([f'v {p.x:.8f} {p.y:.8f} {p.z:.8f}',f'vt {t.x:.8f} {t.y:.8f}',f'vn {n.x:.8f} {n.y:.8f} {n.z:.8f}'])
    lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(index,index+3)));index+=3
(ROOT/'Sources/M4A1/scout_optimized.obj').write_text('\n'.join(lines)+'\n')
vmdl=folder/'scout.vmdl';vmdl.write_text(vmdl.read_text().replace('/scout.obj','/scout_optimized.obj'))
(ROOT/'Sources/M4A1/scout-mesh-report.json').write_text(json.dumps({'source_triangles':len(faces),'shipped_triangles':len(mesh.loop_triangles)},indent=2)+'\n')
print('Scout triangles:',len(faces),'->',len(mesh.loop_triangles))
