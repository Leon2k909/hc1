"""Prepare matched whole-object views using the established offline renderer."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Collider/equipment-case-trial-v1/render.py').read_text()
s=s.replace('asset-improvement-20261029/equipment-case','asset-improvement-20261030/pump-skid')
s=s.replace('equipment-case-trial-v1','pump-skid-trial-v1')
s=s.replace("    if name=='before' and not (directory/'before.obj').exists():\n        directory=ROOT/'output/collider-case-accepted-20261029/retired-before-resources'\n",'')
s=s.replace('scene.cycles.samples=48','scene.cycles.samples=24')
s=s.replace('scene.render.threads=4','scene.render.threads=2;scene.cycles.device=\'CPU\'')
s=s.replace("views=[('main',(3.5,-4.6,3.3),(0,0,.85)),('detail',(2.25,-3.5,1.85),(.35,-.55,.95))]",
    "views=[('main',(4.2,-5.3,3.1),(0,0,.94)),('rear',(-4.2,5.6,3.25),(0,0,.94))]")
s=s.replace("data.lens=54. if view=='main' else 67.","data.lens=54.")
s=s.replace("report={'renderer':", "from bpy_extras.object_utils import world_to_camera_view\nmanifest=json.loads((OUT/'manifest.json').read_text())\nsha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()\nprotected=manifest['protectedSourceSHA256']\nfor p,h in protected.items():assert sha(ROOT/p)==h,p\nproposal={p.relative_to(ROOT).as_posix():sha(p) for directory in (ASSETS/RESOURCE,ASSETS/'materials/collider/pump-skid-trial-v1') for p in directory.iterdir() if p.is_file()}\nreport={'renderer':")
s=s.replace("for view,eye,target in views:","after_only='--after-only' in sys.argv\nif after_only:\n    previous=json.loads((OUT/'render-report.json').read_text())\n    for p,h in previous['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p\n    for ext in ('.obj','.mtl','.vmdl'):\n        p=ASSETS/RESOURCE/('before'+ext)\n        assert sha(p)==previous['proposalSourceSHA256'][p.relative_to(ROOT).as_posix()]\n    report['images']=[r for r in previous['images'] if r['variant']=='before']\n    for r in report['images']:assert sha(OUT/r['file'])==r['sha256']\n    report['unchangedBeforeViewsReused']=True\nfor view,eye,target in views:")
s=s.replace("    for variant,objects in (('before',before),('after',after)):\n", "    for variant,objects in (('before',before),('after',after)):\n        if after_only and variant=='before':continue\n")
s=s.replace("'samples':scene.cycles.samples,", "'fullObjectInAllViews':True,'CPUThreads':2,'GPUUsed':False,'protectedSourceSHA256':protected,'proposalSourceSHA256':proposal,'samples':scene.cycles.samples,")
s=s.replace("    data.lens=54.\n    for variant", "    data.lens=54.\n    bpy.context.view_layer.update()\n    for obj in before+after:\n        for corner in obj.bound_box:\n            p=world_to_camera_view(scene,camera,obj.matrix_world@Vector(corner))\n            assert .025<p.x<.975 and .025<p.y<.975 and p.z>0,('Object cropped',view,obj.name,tuple(p))\n    for variant")
s=s.replace("(OUT/'render-report.json').write_text", "for p,h in {**protected,**proposal}.items():assert sha(ROOT/p)==h,p\n(OUT/'render-report.json').write_text")
s=s.replace('print(json.dumps(report))',"print('Both full-object comparisons completed; original map sources unchanged.',flush=True)")
(HERE/'render.py').write_text(s,encoding='utf-8');compile(s,str(HERE/'render.py'),'exec')
wrapper=(ROOT/'Sources/Collider/cooling-unit-trial-v1/render_low_impact.py').read_text()
wrapper=wrapper.replace('cooling-unit','pump-skid')
wrapper=wrapper.replace('childproc=psutil.Process(child.pid);childproc.cpu_affinity(cpus)',
    'childproc=psutil.Process(child.pid);childproc.cpu_affinity(cpus)\n    assert childproc.cpu_affinity()==cpus\n    assert childproc.nice()==psutil.IDLE_PRIORITY_CLASS')
(HERE/'render_low_impact.py').write_text(wrapper,encoding='utf-8')
print('Prepared two matched full-object views: front three-quarter and rear three-quarter.')
