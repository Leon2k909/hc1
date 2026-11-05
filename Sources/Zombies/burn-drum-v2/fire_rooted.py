"""Native three-angle motion QA for flames attached to the drum's actual fuel; leaves the user's session alone."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Sources/Spillway/hose-coil-v2'))
from native import Editor

WORK = ROOT / 'output/riverside' / (sys.argv[1] if len(sys.argv)>1 else 'drum-fire-rooted')
WORK.mkdir(parents=True, exist_ok=True)
code = (ROOT / 'Sources/Zombies/cooler-v2/capture_engine.cs.txt').read_text()
code = code.replace('output/asset-improvement-20261030/cooler/engine', WORK.relative_to(ROOT).as_posix()+'/after')
code = code.replace('var oldCooler = Model.Load("models/compare_old/old_cooler.vmdl");', 'var oldCooler = cooler;')
a = code.index('var views = ')
b = code.index('\nvar scene = ', a)
code = code[:a] + '''var views = new (string Name, Vector3 Eye, Vector3 Target, float Fov, bool Cooler)[]
{
    ("front", drum + new Vector3(62,-42,48), drum + Vector3.Up*31, 55f, false),
    ("above", drum + new Vector3(38,-34,64), drum + Vector3.Up*30, 60f, false),
    ("side", drum + new Vector3(-62,-30,44), drum + Vector3.Up*30, 55f, false),
    ("back", drum + new Vector3(-62,42,48), drum + Vector3.Up*36, 55f, false),
    ("low", drum + new Vector3(65,2,35), drum + Vector3.Up*40, 55f, false),
};
''' + code[b:]
code = code.replace('new[] { "before", "after" }', 'new[] { "after" }')
code = code.replace('for (var frame = 0; frame < 24; frame++)', 'for (var frame = 0; frame < 180; frame++)')
code = code.replace('    var written = new System.Collections.Generic.List<string>();', '''    var written = new System.Collections.Generic.List<string>();
    var anchors = new System.Collections.Generic.Dictionary<string, Vector3>();
    var frames = new System.Collections.Generic.Dictionary<string, System.Collections.Generic.HashSet<int>>();
    var checkedBases = 0; var escapedBases = 0; var maxReach = 0f; var maxDrift = 0f; var maxRoll = 0f;
''')
target = '                await Task.Delay(16, cancellationToken);'
code = code.replace(target, '''                foreach (var controller in scene.GetAllComponents<Facepunch.BarrelFlameParticles>())
                    foreach (var p in controller.GameObject.Components.Get<ParticleEffect>().Particles)
                    {
                        if (p.Alpha < .05f) continue;
                        checkedBases++;
                        var bottom = p.Position - Vector3.Up * p.Size.y * .5f;
                        var key = controller.Id.ToString() + ":" + p.StartScale;
                        if (!frames.ContainsKey(key)) frames[key]=new();
                        frames[key].Add((int)MathF.Floor(p.SequenceTime.y*64f));
                        if (anchors.TryGetValue(key, out var original)) maxDrift = MathF.Max(maxDrift, original.Distance(bottom));
                        else anchors[key] = bottom;
                        var reach = (p.Position-controller.OpeningOrigin).WithZ(0).Length + p.Size.x*.5f;
                        maxReach = MathF.Max(maxReach,reach);
                        maxRoll = MathF.Max(maxRoll,MathF.Abs(p.Angles.roll));
                        if (reach>controller.OpeningRadius+.1f) escapedBases++;
                    }
                if (view.Name == "front" && frame % 2 == 0)
                    System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, $"motion-{frame:000}.png"), bitmap.ToPng());
''' + target)
code = code.replace('        Before = before, Game.IsPlaying,', '''        Before = before, Game.IsPlaying,
        Controllers = scene.GetAllComponents<Facepunch.BarrelFlameParticles>().Count(),
        AttachedToLogs = scene.GetAllComponents<Facepunch.BarrelFlameParticles>().Count(c=>c.AttachedToFuel),
        RefractingPlumes = scene.GetAllComponents<ParticleSpriteRenderer>().Count(c=>c.GameObject.Name=="Hot Air" && c.Refraction),
        MinimumAnimationFrames = frames.Values.Min(f=>f.Count),
        Anchors = anchors.Count, CheckedBases=checkedBases, EscapedBases=escapedBases,
        MaximumBaseReach=maxReach, MaximumRootDrift=maxDrift, MaximumRoll=maxRoll,
''')
with Editor() as editor:
    result = editor.script(code, 'capture-rooted-fire.cs')
    (WORK / 'validation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2),flush=True)
    assert result['Controllers'] == result['AttachedToLogs'] == 12 and result['RefractingPlumes']==0
    assert result['MinimumAnimationFrames']>=60
    assert result['Anchors'] == 84 and result['CheckedBases'] > 10000
    assert result['EscapedBases'] == 0 and result['MaximumRootDrift'] < .001 and result['MaximumRoll'] == 0
    assert result['SourceUnchanged'] and not result['ErrorModels']
