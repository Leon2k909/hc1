from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
text=(ROOT/'Sources/Boxyard/pipe-stacks-v1/context.cs.txt').read_text().replace('boxyard/pipe-stacks-v1','sewage/crane-blocks-v1').replace('maps/Boxyard/boxyard.scene','maps/sewage/sewage.scene').replace('"Boxyard"','"Sewage"')
scene=json.loads((ROOT/'Assets/scenes/maps/sewage/sewage.scene').read_text())
names=[g['Name'] for g in scene['GameObjects'] if 'Name' in g and any(t in json.dumps(g) for t in ('Sandbox.ModelRenderer','Sandbox.SkyBox2D','Sandbox.DirectionalLight','Sandbox.EnvmapProbe','Sandbox.Tonemapping','Sandbox.GradientFog','Sandbox.PointLight','Sandbox.SpotLight'))]
start=text.index('var visual =');end=text.index('var root =',start)
text=text[:start]+'var visual = new System.Collections.Generic.HashSet<string>(StringComparer.OrdinalIgnoreCase) {'+','.join(json.dumps(n) for n in names)+'};\n'+text[end:]
start=text.index('    var views = new[] {');end=text.index('    var wanted =',start)
text=text[:start]+'''    var views = new[] {
        (Name: "block", Eye: new Vector3(760f,-320f,840f), Target: new Vector3(610f,-20f,765f), Fov: 50f),
    };
'''+text[end:]
(HERE/'context.cs.txt').write_text(text)
p=ROOT/'output/sewage/crane-blocks-v1/context';p.mkdir(exist_ok=True)
if not (p/'config.json').exists():(p/'config.json').write_text(json.dumps(dict(phase='before',width=1440,height=1000,settle_frames=25,stream_frames=25)))
