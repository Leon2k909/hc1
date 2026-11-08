"""Blender background-only distance mesh reduction; approved base OBJ is unchanged."""
from pathlib import Path
import bpy,json
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/ares/control-console-native-v1';FOLDER=OUT/'stage/Assets/models/props/ares/control_console_native_v1'
v=[];uv=[];normals=[];faces=[];paints=[];paint=None
for line in (FOLDER/'console.obj').read_text().splitlines():
 s=line.split()
 if not s:continue
 if s[0]=='v':v.append(tuple(map(float,s[1:])))
 elif s[0]=='vt':uv.append(tuple(map(float,s[1:])))
 elif s[0]=='vn':normals.append(tuple(map(float,s[1:])))
 elif s[0]=='usemtl':paint=s[1]
 elif s[0]=='f':faces.append([[int(i)-1 for i in t.split('/')] for t in s[1:]]);paints.append(paint)
counts=[len(faces)]
for lod,ratio in ((1,.23),(2,.075)):
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 mesh=bpy.data.meshes.new('Console distance mesh');mesh.from_pydata(v,[],[[t[0] for t in f] for f in faces]);mesh.update()
 obj=bpy.data.objects.new('Console',mesh);bpy.context.collection.objects.link(obj);bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 names=list(dict.fromkeys(paints))
 for name in names:mesh.materials.append(bpy.data.materials.new(name))
 layer=mesh.uv_layers.new(name='UVMap')
 custom=[]
 for poly,f,name in zip(mesh.polygons,faces,paints):
  poly.material_index=names.index(name);poly.use_smooth=True
  for li,t in zip(poly.loop_indices,f):layer.data[li].uv=uv[t[1]];custom.append(normals[t[2]])
 mesh.normals_split_custom_set(custom)
 modifier=obj.modifiers.new('Distance reduction','DECIMATE');modifier.ratio=ratio;modifier.use_collapse_triangulate=True
 bpy.ops.object.modifier_apply(modifier=modifier.name);mesh=obj.data;mesh.calc_loop_triangles()
 lines=['mtllib console.mtl','o console_lod'+str(lod)];offset=1;triangles=0
 # Full corner tuples retain interpolated UVs and split normals after reduction.
 for tri in mesh.loop_triangles:
  lines.append('usemtl '+names[mesh.polygons[tri.polygon_index].material_index])
  for vi,li in zip(tri.vertices,tri.loops):
   p=mesh.vertices[vi].co;t=mesh.uv_layers.active.data[li].uv;n=mesh.corner_normals[li].vector
   lines.extend([f'v {p.x:.7f} {p.y:.7f} {p.z:.7f}',f'vt {t.x:.7f} {t.y:.7f}',f'vn {n.x:.7f} {n.y:.7f} {n.z:.7f}'])
  lines.append('f '+' '.join(f'{i}/{i}/{i}' for i in range(offset,offset+3)));offset+=3;triangles+=1
 (FOLDER/f'console_lod{lod}.obj').write_text('\n'.join(lines)+'\n');counts.append(triangles)
doc=(FOLDER/'console.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
res='models/props/ares/control_console_native_v1'
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{res}/'+('console.obj' if i==0 else f'console_lod{i}.obj')+'" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = { exclude_by_default = false exception_list = [] } },' for i in range(3))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {distance} meshes = ["lod{i}"] }},' for i,distance in enumerate((0,25,65)))
(FOLDER/'console.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {meshes} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
(OUT/'lods.json').write_text(json.dumps({'triangles':counts,'thresholds':[0,25,65],'base_unchanged':True},indent=2));print('CONSOLE_LODS',counts)
