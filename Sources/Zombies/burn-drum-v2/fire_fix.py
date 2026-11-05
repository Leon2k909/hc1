"""Inspect, capture and validate the drum-fire fit using native s&box. No play-session or viewport changes."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Sources/Spillway/hose-coil-v2'))
from native import Editor

WORK = ROOT / 'output/riverside' / (sys.argv[2] if len(sys.argv)>2 else 'drum-fire-fit')
WORK.mkdir(parents=True, exist_ok=True)
MODE = sys.argv[1]
with Editor() as editor:
    if MODE == 'inspect':
        result = editor.script('''var scene = Editor.SceneEditorSession.Active.Scene;
return new { scene.Name, Fires=scene.GetAllComponents<Facepunch.MapFire>().Select(f => new { f.Id, f.GameObject.Name, f.WorldPosition, f.Width, f.FlameHeight }).ToArray(),
ParticleEffectProperties=typeof(ParticleEffect).GetProperties().Select(p=>p.Name).ToArray() };''','inspect-drum-fires.cs')
        print(json.dumps(result,indent=2))
        for query in ('set component', 'save_scene', 'compile_status'):
            result = editor.call('search_tools',dict(query=query))
            print(json.dumps([t for t in result['tools'] if t['name'] in ('set_component_property','set_component_properties','save_scene','compile_status')],indent=2))
    elif MODE in ('compile','status'):
        result = editor.call('compile_status')
        summary = dict(IsBuilding=result['IsBuilding'], Compilers=[dict(Name=c['Name'], Success=c['Success'], Errors=c['Errors'],
            Diagnostics=[d for d in c.get('Diagnostics',[]) if d.get('Severity')=='Error']) for c in result['Compilers']])
        print(json.dumps(summary,indent=2))
        (WORK / 'compile-status.json').write_text(json.dumps(summary,indent=2))
        if MODE == 'compile':
            catalog = editor.call('search_tools',dict(query='component'))
            for tool in catalog['tools']:
                if tool['name'].startswith('set_'):
                    print(json.dumps(tool,indent=2))
    elif MODE == 'verify':
        before = json.loads((WORK / 'riverside-before.scene').read_text())
        after = json.loads((ROOT / 'Assets/scenes/maps/Riverside/riverside.scene').read_text())
        def walk(node):
            if isinstance(node,dict):
                yield node
                for child in node.values():
                    yield from walk(child)
            elif isinstance(node,list):
                for child in node:
                    yield from walk(child)
        changed = 0
        for item in walk(before):
            if item.get('__type') != 'Facepunch.MapFire':
                continue
            item.setdefault('OpeningRadius',0)
            item.setdefault('OpeningHeight',0)
            if item.get('Width') == 18 and item.get('FlameHeight') == 44:
                item.update(Width=12,FlameHeight=30,FlamesPerSecond=18,OpeningRadius=9.5,OpeningHeight=7.59)
                changed += 1
        assert changed == 12
        assert before == after, 'Saved scene changed beyond drum-fire settings and new zero-valued defaults.'
        capture = json.loads((WORK / 'after-capture.json').read_text())
        assert capture['CheckedBases'] > 1000 and capture['EscapedBases'] == 0 and not capture['ErrorModels']
        assert capture['SourceUnchanged']
        report = dict(SavedDrums=changed,OtherSceneDataPreserved=True,ParticleSamples=capture['CheckedBases'],
                      EscapedBases=0,MaximumBaseReach=capture['MaximumBaseReach'],OpeningRadius=9.5)
        (WORK / 'validation.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    elif MODE == 'apply':
        state = editor.script('''var scene = Editor.SceneEditorSession.Active.Scene;
if (scene.Source?.ResourcePath?.Equals("scenes/maps/riverside/riverside.scene",StringComparison.OrdinalIgnoreCase) != true)
    throw new InvalidOperationException("Riverside must remain the edited document.");
object Fires(Scene s) => s?.GetAllComponents<Facepunch.MapFire>().Where(f => f.Width <= 18 && f.FlameHeight <= 44)
    .Select(f => new { Component=f.Id, Object=f.GameObject.Id, f.GameObject.Name, f.WorldPosition, f.Width, f.FlameHeight, f.FlamesPerSecond, f.OpeningRadius, f.OpeningHeight }).ToArray();
var backup = System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/drum-fire-fit/riverside-before.scene");
if (!System.IO.File.Exists(backup)) System.IO.File.Copy(System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"Assets/scenes/maps/Riverside/riverside.scene"),backup,false);
return new { Edited=Fires(scene), Runtime=Game.IsPlaying ? Fires(Game.ActiveScene) : null, Game.IsPlaying };''','drum-fit-state.cs')
        (WORK / 'apply-before.json').write_text(json.dumps(state,indent=2))
        assert len(state['Edited']) == 12, 'Expected exactly 12 burning drums.'
        properties = dict(Width=12,FlameHeight=30,FlamesPerSecond=18,OpeningRadius=9.5,OpeningHeight=7.59)
        applied = []
        for fire in state['Edited']:
            result = editor.call('set_component',dict(id=fire['Component'],properties=properties))
            applied.append(result)
            (WORK / 'apply-progress.json').write_text(json.dumps(applied,indent=2))
        print(json.dumps(editor.call('save_scene')),flush=True)
        runtime = []
        if state['IsPlaying']:
            assert len(state['Runtime']) == 12, 'Unexpected running drum count; saved edit is applied, inspect runtime before retry.'
            for fire in state['Runtime']:
                for name, value in properties.items():
                    runtime.append(editor.call('set_runtime_property',dict(id=fire['Object'],component='MapFire',property=name,value=value)))
        (WORK / 'apply-result.json').write_text(json.dumps(dict(Edited=applied,Runtime=runtime),indent=2))
        print(json.dumps(dict(SavedDrums=len(applied),LiveDrums=len(state['Runtime'] or []),WasPlaying=state['IsPlaying'])),flush=True)
    elif MODE in ('before','after'):
        code = (ROOT / 'Sources/Zombies/cooler-v2/capture_engine.cs.txt').read_text()
        # Use only the native visual-scene setup and streaming. The old cooler comparison is not needed.
        code = code.replace('output/asset-improvement-20261030/cooler/engine', WORK.relative_to(ROOT).as_posix() + '/' + MODE)
        code = code.replace('var oldCooler = Model.Load("models/compare_old/old_cooler.vmdl");', 'var oldCooler = cooler;')
        a = code.index('var views = new ')
        b = code.index('\nvar scene = Scene.CreateEditorScene();', a)
        code = code[:a] + '''var views = new (string Name, Vector3 Eye, Vector3 Target, float Fov, bool Cooler)[]
{
    ("front", drum + new Vector3(62,-42,48), drum + Vector3.Up*31, 55f, false),
    ("above", drum + new Vector3(38,-34,64), drum + Vector3.Up*30, 60f, false),
    ("side", drum + new Vector3(-62,-30,44), drum + Vector3.Up*30, 55f, false),
};
''' + code[b:]
        code = code.replace('new[] { "before", "after" }','new[] { "after" }')
        code = code.replace('for (var frame = 0; frame < 24; frame++)','for (var frame = 0; frame < 100; frame++)')
        # Keep a sequence from the first camera to inspect more than one moment of the moving fire.
        target = '                await Task.Delay(16, cancellationToken);'
        inject = '''                if (view.Name == "front" && frame >= 20 && frame % 15 == 0)
                    System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, $"front-{frame:000}.png"), bitmap.ToPng());
'''
        code = code.replace(target, inject + target)
        if MODE == 'after':
            code = code.replace('    var written = new System.Collections.Generic.List<string>();',
                '    var written = new System.Collections.Generic.List<string>();\n    var checkedBases = 0; var escapedBases = 0; var maxReach = 0f;')
            measurement = '''                foreach (var controller in scene.GetAllComponents<Facepunch.FlameParticles>().Where(c=>c.OpeningRadius>0))
                    foreach (var particle in controller.GameObject.Components.Get<ParticleEffect>().Particles)
                    {
                        var angle=particle.Angles.roll*MathF.PI/180f;
                        var c=MathF.Abs(MathF.Cos(angle)); var s=MathF.Abs(MathF.Sin(angle));
                        var halfWidth=(particle.Size.x*c+particle.Size.y*s)*.5f;
                        var halfHeight=(particle.Size.y*c+particle.Size.x*s)*.5f;
                        if (particle.Alpha < .05f || particle.Position.z-halfHeight > controller.OpeningOrigin.z+controller.OpeningHeight) continue;
                        checkedBases++;
                        var reach=(particle.Position-controller.OpeningOrigin).WithZ(0).Length+halfWidth;
                        maxReach=MathF.Max(maxReach,reach);
                        if (reach>controller.OpeningRadius+.1f) escapedBases++;
                    }
'''
            code = code.replace(target,measurement+target)
            code = code.replace('        Before = before, Game.IsPlaying,','        Before = before, Game.IsPlaying, CheckedBases=checkedBases, EscapedBases=escapedBases, MaximumBaseReach=maxReach,')
        result = editor.script(code,'capture-drum-fire-' + MODE + '.cs')
        (WORK / (MODE + '-capture.json')).write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
