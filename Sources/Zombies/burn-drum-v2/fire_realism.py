"""Persist and verify the refined drum-fire profile using native s&box. python fire_realism.py apply|verify"""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0,str(ROOT / 'Sources/Spillway/hose-coil-v2'))
from native import Editor

WORK = ROOT / 'output/riverside/drum-fire-realism'
WORK.mkdir(parents=True,exist_ok=True)
PROFILE = dict(FlamesPerSecond=24,SmokePerSecond=2,SmokeSize=48,SmokeLife=4.5,EmbersPerSecond=2,LightBrightness=2.2)
if sys.argv[1] == 'apply':
    with Editor() as editor:
        state = editor.script('''var scene=Editor.SceneEditorSession.Active.Scene;
if (scene.Source?.ResourcePath?.Equals("scenes/maps/riverside/riverside.scene",StringComparison.OrdinalIgnoreCase)!=true)
    throw new InvalidOperationException("Riverside must be the edited document.");
object Fires(Scene s)=>s?.GetAllComponents<Facepunch.MapFire>().Where(f=>f.OpeningRadius>0)
    .Select(f=>new { Component=f.Id,Object=f.GameObject.Id,f.GameObject.Name }).ToArray();
var backup=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/drum-fire-realism/riverside.before.scene");
if (!System.IO.File.Exists(backup)) System.IO.File.Copy(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"Assets/scenes/maps/Riverside/riverside.scene"),backup,false);
return new { Edited=Fires(scene),Runtime=Game.IsPlaying ? Fires(Game.ActiveScene):null,Game.IsPlaying };''','drum-realism-state.cs')
        assert len(state['Edited']) == 12
        (WORK / 'apply-before.json').write_text(json.dumps(state,indent=2))
        applied=[]
        for fire in state['Edited']:
            applied.append(editor.call('set_component',dict(id=fire['Component'],properties=PROFILE)))
            (WORK / 'apply-progress.json').write_text(json.dumps(applied,indent=2))
        saved=editor.call('save_scene')
        print(json.dumps(saved),flush=True)
        runtime=[]
        if state['IsPlaying']:
            assert len(state['Runtime'])==12
            for fire in state['Runtime']:
                for name,value in PROFILE.items():
                    runtime.append(editor.call('set_runtime_property',dict(id=fire['Object'],component='MapFire',property=name,value=value)))
        (WORK / 'apply-result.json').write_text(json.dumps(dict(Saved=saved,Edited=applied,Runtime=runtime),indent=2))
        print('Saved the realistic profile on 12 burning drums.',flush=True)
elif sys.argv[1] == 'verify':
    before=json.loads((WORK / 'riverside.before.scene').read_text())
    after=json.loads((ROOT / 'Assets/scenes/maps/Riverside/riverside.scene').read_text())
    def walk(node):
        if isinstance(node,dict):
            yield node
            for value in node.values():yield from walk(value)
        elif isinstance(node,list):
            for value in node:yield from walk(value)
    count=0
    for node in walk(before):
        if node.get('__type')=='Facepunch.MapFire' and node.get('OpeningRadius',0)>0:
            node.update(PROFILE)
            count+=1
    assert count==12 and before==after,'Saved data changed beyond the 12 drum-fire profiles.'
    capture=json.loads((WORK / 'after-capture.json').read_text())
    assert capture['CheckedBases']>1000 and capture['EscapedBases']==0 and capture['SourceUnchanged'] and not capture['ErrorModels']
    report=dict(SavedDrums=count,OtherSceneDataPreserved=True,ParticleSamples=capture['CheckedBases'],EscapedBases=0,
                MaximumRotatedBaseReach=capture['MaximumBaseReach'],OpeningRadius=9.5,Profile=PROFILE)
    (WORK / 'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
