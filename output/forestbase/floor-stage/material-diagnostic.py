import bpy,sys,json
from pathlib import Path
p=Path.cwd()/'Tools/forestbase_forest_preview.py'
sys.argv=['diagnostic','--','--revision','floor','--state','after','--view','grass-detail','--lod','lod0']
g={'__file__':str(p),'__name__':'__main__'}
exec(compile(p.read_text().split('bpy.ops.render.render(write_still=True)')[0],str(p),'exec'),g)
report=[]
for o in bpy.data.objects:
 if not o.name.startswith('Forest floor grass '):continue
 for mat in o.data.materials:
  ns=mat.node_tree.nodes
  report.append(dict(object=o.name,color=list(o.color),shadow=o.visible_shadow,material=mat.name,nodes=[dict(name=n.name,type=n.bl_idname,image=n.image.filepath if n.bl_idname=='ShaderNodeTexImage' else None) for n in ns],links=[(l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in mat.node_tree.links]))
Path('output/forestbase/floor-stage/material-diagnostic.json').write_text(json.dumps(report,indent=2))
