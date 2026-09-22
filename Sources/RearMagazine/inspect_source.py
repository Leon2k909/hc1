import bpy, json
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[2]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(root/'Assets/Weapons/swb/scarh/models/scar.fbx'))
report=[]
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':
        points=[obj.matrix_world @ Vector(p) for p in obj.bound_box]
        report.append({'name':obj.name,'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)],'groups':[g.name for g in obj.vertex_groups]})
    if obj.type=='ARMATURE':
        report.append({'skeleton':obj.name,'bones':{b.name:list(obj.matrix_world @ b.head_local) for b in obj.data.bones if any(s in b.name.lower() for s in ['base','mag','grip'])}})
out=root/'Sources/RearMagazine/qa';out.mkdir(parents=True,exist_ok=True)
(out/'scar-source.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
