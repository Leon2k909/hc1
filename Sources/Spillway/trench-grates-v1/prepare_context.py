from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
text=(ROOT/'Sources/Riverside/searchlight-v1/context.cs.txt').read_text()
text=text.replace('riverside/searchlight-v1','spillway/trench-grates-v1').replace('maps/riverside/riverside.scene','maps/spillway/spillway.scene').replace('"Riverside"','"Spillway"').replace('"Moon"','"Sun"')
start=text.index('    var views = new[] {');end=text.index('    var wanted =',start)
text=text[:start]+'''    var views = new[] {
        (Name: "grate", Eye: new Vector3(440f,-620f,155f), Target: new Vector3(330f,-460f,0f), Fov: 52f),
    };
'''+text[end:]
(HERE/'context.cs.txt').write_text(text)
p=ROOT/'output/spillway/trench-grates-v1/context';p.mkdir(exist_ok=True)
if not (p/'config.json').exists():(p/'config.json').write_text(json.dumps(dict(phase='before',width=1440,height=1000,settle_frames=30,stream_frames=30)))
