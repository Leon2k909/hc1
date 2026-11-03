from pathlib import Path
import json

root=Path(__file__).resolve().parents[3]
here=Path(__file__).resolve().parent
out=root/'output/spillway/waterline-fix-v1'
out.mkdir(parents=True,exist_ok=True)
s=(root/'Sources/Spillway/editor/capture.cs.txt').read_text()
s=s.replace('output/spillway/captures','output/spillway/waterline-fix-v1')
s=s.replace('"Volumetric Fog"','"Volumetric Fog", "Spillway indirect light"')
start=s.index('    var views = new[] {')
end=s.index('    var wanted =', start)
s=s[:start]+'''    var views = new[] {
        (Name: "waterline", Eye: new Vector3(0,-2000,-181), Target: new Vector3(0,-5200,-181), Fov: 80f),
        (Name: "downstream", Eye: new Vector3(-1650,-1750,64), Target: new Vector3(0,-6000,-30), Fov: 80f),
        (Name: "bank", Eye: new Vector3(1750,-2200,-100), Target: new Vector3(3400,-4400,-100), Fov: 80f),
    };
'''+s[end:]
s=s.replace('view.Name + ".png"','view.Name + "-" + configuration["phase"].GetValue<string>() + ".png"')
(here/'capture.cs.txt').write_text(s)
(out/'config.json').write_text(json.dumps(dict(phase='before',width=1500,height=900,settle_frames=32,stream_frames=30),indent=2))
