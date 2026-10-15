"""Historical bootstrap for Orion's original native lighting scripts.

The checked-in editor scripts now include map-specific fixes. This tool must not
overwrite them; use them directly from the current CLI exchange directory.
"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'Sources/Orion/editor'
if (out/'bake-lighting.cs.txt').exists():
    raise SystemExit('Orion lighting scripts already exist; preserve the map-specific versions.')
source=(ROOT/'Sources/Collider/editor/bake-lighting.cs.txt').read_text()
source=source.replace('collider','orion').replace('Collider','Orion')
source=source.replace('reflections.Length != 4','reflections.Length != 0')
source='\n'.join(line for line in source.splitlines() if 'reflections[0].GameObject.Parent' not in line)
source=source.replace('completed = true;', 'typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);\n    completed = true;')
(out/'bake-lighting.cs.txt').write_text(source)
(ROOT/'output/orion/bake-config.json').write_text(json.dumps({'directory':'lighting-v1','timeout_seconds':600},indent=2))

source=(ROOT/'Sources/Collider/editor/capture-reflections.cs.txt').read_text()
source=source.replace('collider','orion').replace('Collider','Orion')
source=source.replace('new[]{"Hall","Beam","West","East"}','new[]{"Yard","Control","Service"}')
source=source.replace('var probe=scene.GetAllComponents<EnvmapProbe>().Single(p=>p.GameObject.Name==label);\nvar position=label=="Beam"?new Vector3(1010,0,540):probe.WorldPosition;',
    'var position=Vector3.Parse(config["position"].GetValue<string>());')
(out/'capture-reflections.cs.txt').write_text(source)

source=(ROOT/'Tools/sewage_reflections.py').read_text().replace('sewage','orion').replace('Sewage','Orion')
source=source.replace("parser.add_argument('index',type=int,choices=range(3))","parser.add_argument('index',choices=('Yard','Control','Service'))")
source=source.replace('linear*2','linear*1.4')
(ROOT/'Tools/orion_reflections.py').write_text(source)

source=(ROOT/'Sources/Collider/editor/apply-reflections.cs.txt').read_text().replace('collider','orion').replace('Collider','Orion')
source=source.replace('new[]{"Hall","Beam","West","East"}','new[]{"Yard","Control","Service"}')
source=source.replace('_v3.vtex','_v1.vtex')
(out/'apply-reflections.cs.txt').write_text(source)
print('Prepared native light bake and static-reflection scripts')
