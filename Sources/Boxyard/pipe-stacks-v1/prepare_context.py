from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
text=(ROOT/'Sources/Spillway/trench-grates-v1/context.cs.txt').read_text()
text=text.replace('spillway/trench-grates-v1','boxyard/pipe-stacks-v1').replace('maps/spillway/spillway.scene','maps/Boxyard/boxyard.scene').replace('"Spillway"','"Boxyard"')
# Boxyard uses its map model roots directly; enumerate names from the saved scene.
scene=json.loads((ROOT/'Assets/scenes/maps/Boxyard/boxyard.scene').read_text());print([g.get('Name','(prefab)') for g in scene['GameObjects']])
start=text.index('    var views = new[] {');end=text.index('    var wanted =',start)
text=text[:start]+'''    var views = new[] {
        (Name: "pipes", Eye: new Vector3(760f,-700f,92f), Target: new Vector3(640f,-816f,13f), Fov: 57f),
        (Name: "east", Eye: new Vector3(666f,-360f,92f), Target: new Vector3(782f,-480f,13f), Fov: 57f),
    };
'''+text[end:]
# Keep all authored visual/environment roots, excluding gameplay components by root name.
names=[g['Name'] for g in scene['GameObjects'] if 'Name' in g and any(t in json.dumps(g) for t in ('Sandbox.ModelRenderer','Sandbox.SkyBox2D','Sandbox.DirectionalLight','Sandbox.EnvmapProbe','Sandbox.Tonemapping','Sandbox.GradientFog'))]
start=text.index('var visual =');end=text.index('var root =',start)
text=text[:start]+'var visual = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase) {'+','.join(json.dumps(n) for n in names)+'};\n'+text[end:]
(HERE/'context.cs.txt').write_text(text)
p=ROOT/'output/boxyard/pipe-stacks-v1/context';p.mkdir(exist_ok=True)
if not (p/'config.json').exists():(p/'config.json').write_text(json.dumps(dict(phase='before',width=1440,height=1000,settle_frames=30,stream_frames=30)))
