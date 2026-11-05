from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
text=(ROOT/'Sources/Sewage/crane-blocks-v1/context.cs.txt').read_text().replace('crane-blocks-v1','salvage-drums-v1')
start=text.index('    var views = new[] {');end=text.index('    var wanted =',start)
text=text[:start]+'''    var views = new[] {
        (Name: "drum", Eye: new Vector3(-450f,-840f,90f), Target: new Vector3(-670f,-680f,27f), Fov: 52f),
        (Name: "location", Eye: new Vector3(-160f,-850f,90f), Target: new Vector3(-650f,-450f,75f), Fov: 78f),
    };
'''+text[end:]
(HERE/'context.cs.txt').write_text(text)
p=ROOT/'output/sewage/salvage-drums-v1/context';p.mkdir(exist_ok=True)
if not (p/'config.json').exists():(p/'config.json').write_text(json.dumps(dict(phase='before',width=1600,height=1000,settle_frames=25,stream_frames=30)))
