from pathlib import Path
import json
root=Path(__file__).resolve().parents[3]
here=Path(__file__).resolve().parent
out=root/'output/spillway/service-cabinet-v1'
s=(root/'Sources/Spillway/editor/capture.cs.txt').read_text()
s=s.replace('output/spillway/captures','output/spillway/service-cabinet-v1/context')
s=s.replace('"Volumetric Fog"','"Volumetric Fog", "Spillway indirect light"')
start=s.index('    var views = new[] {');end=s.index('    var wanted =',start)
s=s[:start]+'''    var views = new[] {
        (Name: "cabinet_pair", Eye: new Vector3(-220,238,67), Target: new Vector3(-302,345,40), Fov: 63f),
        (Name: "cabinet_front", Eye: new Vector3(-285,245,63), Target: new Vector3(-302,345,39), Fov: 55f),
    };
'''+s[end:]
s=s.replace('view.Name + ".png"','view.Name + "-" + configuration["phase"].GetValue<string>() + ".png"')
s=s.replace('camera.RenderToBitmap(bitmap);','camera.RenderToBitmap(bitmap,false);')
# Preserve the two baseline visibility tests as a matched context comparison.
s=s.replace('    var missing =', '''    var rays=new System.Collections.Generic.List<object>();
    using(scene.Push()) {
     foreach(var e in new[]{-325f,-280f}) {
      var hit=scene.Trace.Ray(World(new Vector3(e,270,40)),World(new Vector3(e,370,40))).Run();
      rays.Add(new{E=e,hit.Hit,At=hit.EndPosition.ToString(),Object=hit.GameObject?.Name});
     }
    }
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,"rays-"+configuration["phase"].GetValue<string>()+".json"),System.Text.Json.JsonSerializer.Serialize(rays));
    var missing =''')
(here/'context.cs.txt').write_text(s)
(out/'context').mkdir(exist_ok=True)
(out/'context/config.json').write_text(json.dumps(dict(phase='before',width=1500,height=1000,settle_frames=40,stream_frames=40),indent=2))
