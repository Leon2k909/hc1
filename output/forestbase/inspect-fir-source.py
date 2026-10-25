import bpy,json
from pathlib import Path
out=[]
for obj in bpy.data.objects:
 if obj.type!='MESH': continue
 obj.data.calc_loop_triangles()
 out.append(dict(name=obj.name,triangles=len(obj.data.loop_triangles),uv=[dict(name=u.name,active_render=u.active_render) for u in obj.data.uv_layers],attrs=[dict(name=a.name,type=a.data_type,domain=a.domain) for a in obj.data.attributes],materials=[s.material.name if s.material else None for s in obj.material_slots],modifiers=[(m.name,m.type) for m in obj.modifiers]))
Path('C:/Users/mimi-/OneDrive/Dokumente/S&box Projects/hc1/output/forestbase/fir-source-uv.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
