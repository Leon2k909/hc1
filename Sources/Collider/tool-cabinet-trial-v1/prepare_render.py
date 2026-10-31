"""Reuse the proven OBJ/PBR renderer for matched whole-cabinet comparisons."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
old=ROOT/'Sources/Collider/pump-skid-trial-v1'
s=(old/'render_realism.py').read_text()
s=s.replace('pump-skid-trial-v1','tool-cabinet-trial-v1')
s=s.replace('location=(0,0,-.005)', 'location=(0,0,-.0003)')
s=s.replace("OUT=ROOT/'output/asset-improvement-20261030/pump-skid/realism-review'", "OUT=ROOT/'output/asset-improvement-20261030/tool-cabinet'")
s=s.replace("OLD=OUT.parent/'revision-01/Assets'\n",'')
s=s.replace("(directory/'after.vmdl')", "(directory/(name+'.vmdl'))")
s=s.replace("(directory/'after.obj')", "(directory/(name+'.obj'))")
s=s.replace("previous=model('previous',OLD);revised=model('revised',ASSETS)","previous=model('before',ASSETS);revised=model('after',ASSETS)")
start=s.index('views=[');end=s.index('report={',start)
s=s[:start]+"views=[('main',(3.25,-4.1,2.60),(0,0,.66)),('rear',(-3.4,4.2,2.55),(0,0,.66))]\n"+s[end:]
s=s.replace("'fullObjectInAllViews':not surface_review", "'fullObjectInAllViews':True")
s=s.replace("sha(OLD/RESOURCE/'after.obj')", "sha(ASSETS/RESOURCE/'before.obj')")
start=s.index("after_only='--after-only'");end=s.index('for view,eye,target in views:',start)
s=s[:start]+s[end:]
s=s.replace("for variant in ('revised','previous'):","for variant in ('after','before'):")
s=s.replace("        if after_only and variant=='previous':continue\n",'')
s=s.replace("        if draft and variant=='previous':continue\n",'')
s=s.replace("        if view=='surface' and variant=='previous':continue", "        if view=='rear' and variant=='before':continue")
s=s.replace("obj.hide_render=variant!='previous'", "obj.hide_render=variant!='before'")
s=s.replace("obj.hide_render=variant!='revised'", "obj.hide_render=variant!='after'")
s=s.replace("(('draft-' if draft else '')+variant+'-'+view+'.png')", "(variant+'-'+view+'.png')")
s=s.replace("('draft-report.json' if draft else 'render-report.json')", "'render-report.json'")
s=s.replace('Matched previous/revised whole-pump comparisons complete; map sources unchanged.',
            'Matched whole-cabinet comparisons complete; map sources unchanged.')
compile(s,str(HERE/'render.py'),'exec');(HERE/'render.py').write_text(s)
w=(old/'render_clean_finish_low_impact.py').read_text()
w=w.replace("output/asset-improvement-20261030/pump-skid/clean-finish-review", "output/asset-improvement-20261030/tool-cabinet")
w=w.replace("'render_clean_finish.py'", "'render.py'")
compile(w,str(HERE/'render_low_impact.py'),'exec');(HERE/'render_low_impact.py').write_text(w)
print('Prepared matched 1600 x 1200 whole-object renders; CPU only, two threads, idle priority.')
