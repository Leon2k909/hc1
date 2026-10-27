import bpy,json
from pathlib import Path
asset=Path(bpy.data.filepath).stem
rows=[]
for obj in bpy.data.objects:
    rows.append({'name':obj.name,'type':obj.type,'faces':len(obj.data.polygons) if obj.type=='MESH' else 0,'location':list(obj.location),'dimensions':list(obj.dimensions),'modifiers':[(m.name,m.type) for m in obj.modifiers],'materials':[slot.material.name if slot.material else None for slot in obj.material_slots]})
folder=Path('C:/Users/mimi-/OneDrive/Dokumente/S&box Projects/hc1/output/forestbase')
(folder/(asset+'-inspect.json')).write_text(json.dumps(rows,indent=2))
print('INSPECT',asset,[(r['name'],r['faces']) for r in rows if r['type']=='MESH'],flush=True)
