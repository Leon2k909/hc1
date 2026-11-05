from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
text=(ROOT/'Sources/Sewage/crane-blocks-v1/context.cs.txt').read_text().replace('sewage/crane-blocks-v1','orion/yard-lamp-v1').replace('maps/sewage/sewage.scene','maps/Orion/orion.scene').replace('"Sewage"','"Orion"')
scene=json.loads((ROOT/'Assets/scenes/maps/Orion/orion.scene').read_text())
names=[g['Name'] for g in scene['GameObjects'] if 'Name' in g and any(t in json.dumps(g) for t in ('Sandbox.ModelRenderer','Sandbox.SkyBox2D','Sandbox.DirectionalLight','Sandbox.EnvmapProbe','Sandbox.Tonemapping','Sandbox.GradientFog','Sandbox.PointLight','Sandbox.SpotLight','Sandbox.AmbientLight'))]
start=text.index('var visual =');end=text.index('var root =',start)
text=text[:start]+'var visual = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase) {'+','.join(json.dumps(n) for n in names)+'};\n'+text[end:]
start=text.index('    var views = new[] {');end=text.index('    var wanted =',start)
text=text[:start]+'''    var views = new[] {
        (Name: "fixture", Eye: new Vector3(215f,116f,74f), Target: new Vector3(181f,166f,95f), Fov: 37f),
        (Name: "location", Eye: new Vector3(120f,65f,72f), Target: new Vector3(181f,166f,50f), Fov: 75f),
    };
'''+text[end:]
(HERE/'context.cs.txt').write_text(text)
p=ROOT/'output/orion/yard-lamp-v1/context';p.mkdir(exist_ok=True)
if not (p/'config.json').exists():(p/'config.json').write_text(json.dumps(dict(phase='before',width=1600,height=1000,settle_frames=35,stream_frames=35)))
