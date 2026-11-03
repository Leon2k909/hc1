from pathlib import Path
import json
from native import call,script,OUT,ROOT
HERE=Path(__file__).parent
print(json.dumps(script(HERE/'import.cs.txt')))
for path in ['materials/ares/observation-sign-v1/face.vmat','models/maps/ares/observation-sign-v1/observation_sign.vmdl','models/maps/ares/observation-sign-v1/dressing_without_sign.vmdl']:
    result=call('asset_compile',dict(path=path,full=True))
    print(json.dumps(result))
    assert result.get('Success'),result
capture=(HERE/'baseline.cs.txt').read_text()
capture=capture.replace('CameraComponent camera;ModelRenderer hall,core;Model oldHall,oldCore;', 'CameraComponent camera;ModelRenderer hall,core,sign;Model oldHall,oldCore;')
capture=capture.replace('models/maps/ares/interior-v1/ares_hall_preview.vmdl','models/maps/ares/observation-sign-v1/dressing_without_sign.vmdl')
capture=capture.replace('models/maps/ares/interior-v1/ares_reactor_preview.vmdl','models/maps/ares/ares_reactor.vmdl')
capture=capture.replace('=="models/maps/ares/ares_hall.vmdl"','=="models/maps/ares/ares_dressing.vmdl"')
capture=capture.replace('oldHall=hall.Model;oldCore=core.Model;','''oldHall=hall.Model;oldCore=core.Model;
  var signObject=new GameObject(false,"Observation sign review only");
  sign=signObject.Components.Create<ModelRenderer>();
  sign.Model=Model.Load("models/maps/ares/observation-sign-v1/observation_sign.vmdl");
  if(sign.Model.IsError)throw new InvalidOperationException("Sign did not compile");''')
capture=capture.replace('hall.Model=variant=="after"?newHall:oldHall;core.Model=variant=="after"?newCore:oldCore;', 'hall.Model=variant=="after"?newHall:oldHall;core.Model=variant=="after"?newCore:oldCore;sign.GameObject.Enabled=variant=="after";')
(HERE/'capture.cs.txt').write_text(capture)
config=json.loads((OUT/'capture-config.json').read_text());config['variants']=['before','after']
(OUT/'capture-config.json').write_text(json.dumps(config,indent=2))
print(json.dumps(script(HERE/'capture.cs.txt'),indent=2))
