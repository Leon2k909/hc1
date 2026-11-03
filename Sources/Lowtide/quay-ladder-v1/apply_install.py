from pathlib import Path
import hashlib,json,sys
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
if '--verify-only' not in sys.argv:
    print(json.dumps(script(HERE/'install.cs.txt')),flush=True)
    for side in ('east','west'):
        path=f'models/maps/lowtide/lowtide_{side}.vmdl'
        result=call('asset_compile',dict(path=path,full=True));print(json.dumps(result),flush=True);assert result['Success']
src=(HERE/'runtime_trial.cs.txt').read_text().replace('runtime-trial','runtime-installed')
start=src.index('  var architecture=');end=src.index('  var holder=',start)
src=src[:start]+src[end:]
start=src.index(' var views=new[]');end=src.index(' foreach(var view in views)',start)
src=src[:start]+''' var views=new System.Collections.Generic.List<(string Name,Vector3 Eye,Vector3 Target,float Fov)>();
 foreach(var s in new[]{1,-1})foreach(var n in new[]{-1450f,-560f,1020f})
  views.Add(($"{(s==1?"east":"west")}-{n}",new Vector3(n-65,-s*158,40),new Vector3(n,-s*240,-6),65f));
'''+src[end:]
(HERE/'runtime_installed.cs.txt').write_text(src)
print(json.dumps(script(HERE/'runtime_installed.cs.txt'),indent=2),flush=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());guard=json.loads((OUT/'install-source-guard.json').read_text())
changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert set(changed)==set(plan['before']),changed
assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
for side in ('east','west'):
    name=f'lowtide_{side}.vmdl';old=(OUT/'install-before'/name).read_text();new=(ROOT/'Assets/models/maps/lowtide'/name).read_text()
    assert old[old.index('_class = "PhysicsShapeList"'):]==new[new.index('_class = "PhysicsShapeList"'):]
    original=(ROOT/f'Assets/models/maps/lowtide/lowtide_{side}.obj').read_text().splitlines()
    trimmed=(ROOT/f'Assets/models/maps/lowtide/quay-ladder-v1/installed/{side}_without_ladders.obj').read_text().splitlines()
    assert [l for l in original if l.startswith(('v ','vt ','vn '))]==[l for l in trimmed if l.startswith(('v ','vt ','vn '))]
check=json.loads((OUT/'runtime-installed/checked.json').read_text());assert check['ActualPlayMode'] and not check['ErrorModels'] and len(check['Written'])==6
status=call('editor_status');assert status['ActiveScenePath']=='scenes/menu.scene' and status['IsPlaying'] and not status['SceneHasUnsavedChanges']
report=dict(installed=True,approved='User approved after play-mode check 2026-11-03',ladders=6,physics_unchanged=True,scene_file_unchanged=True,other_assets_unchanged=True,changed_original_assets=changed,counts=plan['counts'],play_mode_check=check,menu_restored=True,editor_status=status)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(installed=True,ladders=6,actual_play_mode_checked=True,menu_restored=True)))
