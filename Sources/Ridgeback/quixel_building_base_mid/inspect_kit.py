import bpy,json
from pathlib import Path
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:/sbox-projects/hc1/forked-shooter-main/Sources/Ridgeback/quixel_building_base_mid/Modular_Building_Base_Kit_wdetbjudw_Mid.fbx')
out=[]
for o in bpy.data.objects:
 if o.type!='MESH':continue
 pts=[o.matrix_world@Vector(p) for p in o.bound_box]
 out.append(dict(name=o.name,vertices=len(o.data.vertices),polygons=len(o.data.polygons),triangles=sum(len(p.vertices)-2 for p in o.data.polygons),location=list(o.location),rotation=list(o.rotation_euler),scale=list(o.scale),mins=[min(p[i] for p in pts) for i in range(3)],maxs=[max(p[i] for p in pts) for i in range(3)],materials=[m.name for m in o.data.materials]))
Path(r'C:/sbox-projects/hc1/forked-shooter-main/output/ridgeback/megascans-outbuilding-v1/kit-meshes.json').write_text(json.dumps(out,indent=2))
