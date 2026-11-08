from pathlib import Path
exec(Path(__file__).with_name('inspect_kit.py').read_text())
import math
from mathutils import Matrix
outdir=Path(r'C:/sbox-projects/hc1/forked-shooter-main/Sources/Ridgeback/quixel_building_base_mid/workshop');outdir.mkdir(exist_ok=True)
originals={o.name[-3:]:o for o in bpy.data.objects if o.type=='MESH'}
manifest=[]
for lod,ratio in enumerate([1.0,0.45,0.16]):
 lines=['mtllib workshop.mtl'];vi=ti=ni=0;triangles=0
 def poly(points,paint,uvs=None):
  global vi,ti,ni,triangles
  lines.append('usemtl '+paint);n=(Vector(points[1])-Vector(points[0])).cross(Vector(points[2])-Vector(points[0])).normalized()
  for p in points:lines.append(f'v {p[1]:.6f} {p[2]:.6f} {p[0]:.6f}')
  for i,p in enumerate(points):
   uv=uvs[i] if uvs else (p[0]/128,p[1]/128)
   lines.append(f'vt {uv[0]:.6f} {uv[1]:.6f}')
   lines.append(f'vn {n.y:.6f} {n.z:.6f} {n.x:.6f}')
  lines.append('f '+' '.join(f'{vi+i+1}/{ti+i+1}/{ni+i+1}' for i in range(len(points))))
  vi+=len(points);ti+=len(points);ni+=len(points);triangles+=len(points)-2
 def box(lo,hi,paint):
  x,y,z=lo;X,Y,Z=hi
  for p in [[(x,y,z),(x,Y,z),(X,Y,z),(X,y,z)],[(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],[(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],[(X,Y,z),(x,Y,z),(x,Y,Z),(X,Y,Z)],[(x,Y,z),(x,y,z),(x,y,Z),(x,Y,Z)],[(X,y,z),(X,Y,z),(X,Y,Z),(X,y,Z)]]:poly(p,paint)
 for name,yaw in [('000',0),('002',90),('003',180),('002',270)]:
  src=originals[name];o=src.copy();o.data=src.data.copy();bpy.context.collection.objects.link(o)
  if ratio<1:
   bpy.context.view_layer.objects.active=o; mod=o.modifiers.new('LOD reduction','DECIMATE');mod.ratio=ratio;bpy.ops.object.modifier_apply(modifier=mod.name)
  mesh=o.data;uv=mesh.uv_layers.active.data;normmat=o.matrix_world.to_3x3().inverted().transposed();c=math.cos(math.radians(yaw));s=math.sin(math.radians(yaw));lines+=['usemtl scanned_brick','s 1']
  def rotate(x,y):return c*x-s*y,s*x+c*y
  for v in mesh.vertices:
   p=o.matrix_world@v.co;x=-p.y*39.37007874+78.74015748;y=p.x*39.37007874-78.74015748;x,y=rotate(x,y);lines.append(f'v {y:.6f} {p.z*39.37007874:.6f} {x:.6f}')
  for loop in mesh.loops:
   t=uv[loop.index].uv;lines.append(f'vt {t.x:.7f} {t.y:.7f}')
  for loop in mesh.loops:
   n=(normmat@mesh.corner_normals[loop.index].vector).normalized();x,y=rotate(-n.y,n.x);lines.append(f'vn {y:.7f} {n.z:.7f} {x:.7f}')
  for p in mesh.polygons:lines.append('f '+' '.join(f'{vi+mesh.loops[i].vertex_index+1}/{ti+i+1}/{ni+i+1}' for i in p.loop_indices));triangles+=len(p.vertices)-2
  vi+=len(mesh.vertices);ti+=len(mesh.loops);ni+=len(mesh.loops);bpy.data.objects.remove(o,do_unlink=True)
 # low foundation, a dark interior backing, and a hipped tile roof
 box((-79,-79,-9),(79,79,1),'concrete')
 box((-70,-70,0),(70,70,156),'trim_brown')
 e=86;z=158;top=208
 for a,b in [((-e,-e,z),(e,-e,z)),((e,-e,z),(e,e,z)),((e,e,z),(-e,e,z)),((-e,e,z),(-e,-e,z))]:
  length=2*e;slope=math.hypot(e,top-z)
  poly([a,b,(0,0,top)],'roof_tiles',[(0,0),(length/128,0),(e/128,slope/128)])
 # eave boards and unobtrusive metal guttering, plus a rear downpipe
 for low,high in [((-86,-86,154),(86,-82,158)),((-86,82,154),(86,86,158)),((-86,-82,154),(-82,82,158)),((82,-82,154),(86,82,158))]:box(low,high,'trim_brown')
 for low,high in [((-87,-87,155),(87,-85,157)),((-87,85,155),(87,87,157)),((-87,-85,155),(-85,85,157)),((85,-85,155),(87,85,157))]:box(low,high,'metal')
 box((-80,-84,-3),(-77,-81,156),'metal')
 (outdir/f'workshop_lod{lod}.obj').write_text('\n'.join(lines)+'\n');manifest.append({'lod':lod,'triangles':triangles})
(outdir/'manifest.json').write_text(json.dumps(manifest,indent=2));print(manifest)
