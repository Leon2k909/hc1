"""Refresh only the before image after correcting constant VMAT colour conversion."""
from pathlib import Path
import hashlib,json,sys
import bpy
ROOT=Path.cwd();HERE=ROOT/'Sources/Riverdale/lifebuoy-trial-v1';OUT=ROOT/'output/asset-improvement-20261031/riverdale-lifebuoy'
sys.path.insert(0,str(ROOT/'Tools'));import belltower_render as R
guard=json.loads((HERE/'source-guard.json').read_text())
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in guard.items())
bpy.ops.wm.open_mainfile(filepath=str(HERE/'lifebuoy_review.blend'))
for paint in json.loads((HERE/'before.json').read_text()):
    material=bpy.data.materials['Installed '+paint]
    p=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    if not p.inputs['Base Color'].is_linked:
        shader,kv=R.parse_vmat('materials/riverdale/'+paint+'.vmat')
        tint=R.floats(kv.get('g_vColorTint','[1 1 1 1]'))[:3]
        p.inputs['Base Color'].default_value=(*(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in tint),1)
scene=bpy.context.scene
states={o.name:o.hide_render for o in scene.objects}
for o in scene.objects:
    if o.type=='MESH' and not o.name.startswith('Same '):
        o.hide_render=not o.name.startswith('Exact saved lifebuoy before')
scene.render.filepath=str(OUT/'before.png');bpy.ops.render.render(write_still=True)
for name,state in states.items():bpy.data.objects[name].hide_render=state
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'lifebuoy_review.blend'))
report=json.loads((OUT/'render-report.json').read_text())
for item in report['images']:
    if item['variant']=='before':item['sha256']=hashlib.sha256((OUT/item['file']).read_bytes()).hexdigest()
report['constantVMATColoursConvertedFromSRGB']=True
(OUT/'render-report.json').write_text(json.dumps(report,indent=2))
print('Before colour conversion corrected; after image and matched camera/lighting unchanged.')
