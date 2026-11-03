from pathlib import Path
from native import ROOT,OUT,script
import json
HERE=Path(__file__).parent
src=(ROOT/'Sources/Lowtide/quay-ladder-v1/runtime_trial.cs.txt').read_text().replace('output/lowtide/quay-ladder-v1/runtime-trial','output/reefhall/pump-v1/runtime-before').replace('scenes/maps/lowtide/lowtide.scene','scenes/maps/reefhall/reefhall.scene')
start=src.index('  var architecture=');end=src.index('  var holder=',start);src=src[:start]+src[end:]
start=src.index(' var views=new[]');end=src.index(' foreach(var view in views)',start)
src=src[:start]+''' var views=new[]{new {Name="pump",Eye=new Vector3(1480,485,80),Target=new Vector3(1610,380,34),Fov=55f},new {Name="inlet",Eye=new Vector3(1520,275,64),Target=new Vector3(1610,375,32),Fov=60f}};
'''+src[end:]
(HERE/'runtime_before.cs.txt').write_text(src)
print(json.dumps(script(HERE/'runtime_before.cs.txt'),indent=2))
