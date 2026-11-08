from pathlib import Path
import sys,json
sys.path.insert(0,'Sources/Belltower/terracotta-pot-v2')
import native
ROOT=Path.cwd();OUT=ROOT/'output/veridant/remove-cases-20261105';native.OUT=OUT
mode=sys.argv[1]
if mode=='sessions':
    print(json.dumps(native.call('run_csharp',{'code':'return Editor.SceneEditorSession.All.Select(s => new { Name = s.Scene.Name, Source = s.Scene.Source?.ResourcePath, s.HasUnsavedChanges }).ToArray();'}),indent=2))
elif mode in ('before','after'):
    for label in ('olive-stack','black-stack'):
        old=json.loads((ROOT/f'output/veridant/quality/cases-v4-final/{label}-camera.json').read_text())['Capture']
        import hashlib
        config={'directory':'remove-cases-20261105','name':mode+'-'+label,'exposure':2.2,'width':900,'height':750,'fov':48,'settle_ms':0,'position':old['Position'],'angles':old['Angles'],'expected_scene_sha256':hashlib.sha256((ROOT/'Assets/scenes/maps/Veridant/veridant.scene').read_bytes()).hexdigest()}
        (OUT/'capture-request.json').write_text(json.dumps(config))
        script=(ROOT/'Sources/Veridant/remove-cases-20261105/capture.cs.txt').read_text()
        path=OUT/'capture.cs.txt';path.write_text(script)
        print(json.dumps(native.script(path,mode+'-'+label)))
elif mode=='publish':
    print(json.dumps(native.script(ROOT/'Sources/Veridant/remove-cases-20261105/publish.cs.txt','publish'),indent=2))
elif mode=='compile':
    for name in ('veridant_buildings','veridant_dress'):
        print(json.dumps(native.call('asset_compile',{'path':f'models/maps/veridant/{name}.vmdl'},'compile-'+name),indent=2))
