from pathlib import Path
import json,sys
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
if '--capture-only' not in sys.argv:
    print(json.dumps(script(HERE/'import.cs.txt')),flush=True)
    for path in ('models/maps/lowtide/quay-ladder-v1/quay_ladder.vmdl','models/maps/lowtide/quay-ladder-v1/east_without_ladder.vmdl'):
        result=call('asset_compile',dict(path=path,full=True));print(json.dumps(result),flush=True);assert result['Success']
src=(HERE/'baseline.cs.txt').read_text()
src=src.replace('CameraComponent camera;ModelRenderer hall,core;Model oldHall,oldCore;', 'CameraComponent camera;ModelRenderer hall,core,ladder;Model oldHall,oldCore;')
src=src.replace('models/maps/ares/interior-v1/ares_hall_preview.vmdl','models/maps/lowtide/quay-ladder-v1/east_without_ladder.vmdl').replace('models/maps/ares/interior-v1/ares_reactor_preview.vmdl','models/maps/lowtide/lowtide_west.vmdl')
src=src.replace('oldHall=hall.Model;oldCore=core.Model;','''oldHall=hall.Model;oldCore=core.Model;
  var replacement=new GameObject(false,"Quay ladder review only");
  ladder=replacement.Components.Create<ModelRenderer>();
  ladder.Model=Model.Load("models/maps/lowtide/quay-ladder-v1/quay_ladder.vmdl");
  if(ladder.Model.IsError)throw new InvalidOperationException("Ladder failed to load");''')
src=src.replace('hall.Model=variant=="after"?newHall:oldHall;core.Model=variant=="after"?newCore:oldCore;', 'hall.Model=variant=="after"?newHall:oldHall;core.Model=variant=="after"?newCore:oldCore;ladder.GameObject.Enabled=variant=="after";')
(HERE/'capture.cs.txt').write_text(src)
config=json.loads((OUT/'capture-config.json').read_text());config['variants']=['before','after']
(OUT/'capture-config.json').write_text(json.dumps(config,indent=2))
result=script(HERE/'capture.cs.txt');print(json.dumps(result,indent=2));assert result['UserStatePreserved'] and not result['ErrorModels']
