"""Matched native map captures with exact editor restoration."""
from pathlib import Path
import json,math,sys
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent

def prepare_capture():
    source=(ROOT/'Sources/Belltower/editor/capture-pending-garden-props-v1.cs.txt').read_text()
    source=source.replace('System.IO.Path.Combine(root, "output/belltower/roof-lock-apply/capture.json")','System.IO.Path.Combine(System.IO.Path.GetTempPath(), "belltower-terracotta-pot-v2/capture.json")')
    source=source.replace('System.IO.Path.Combine(root, "output/belltower/quality", folder)','System.IO.Path.Combine(System.IO.Path.GetTempPath(), "belltower-terracotta-pot-v2", folder)')
    source=source.replace('Sources/Belltower/editor/capture-pending-garden-props-v1.cs.txt','Sources/Belltower/terracotta-pot-v2/capture.cs.txt')
    source=source.replace('object captured = null;', '''var candidate=config["candidate"]?.GetValue<bool>()==true;
var west=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath=="models/maps/belltower/belltower_west.vmdl");
var westModel=west.Model;
var westSerialized=west.Serialize().ToJsonString();
var baseModel=candidate ? Model.Load("models/maps/belltower/terracotta-pot-v2/west_without_one_pot.vmdl") : null;
var potModel=candidate ? Model.Load("models/maps/belltower/terracotta-pot-v2/terracotta_pot.vmdl") : null;
if(candidate && (baseModel is null || baseModel.IsError || potModel is null || potModel.IsError))throw new InvalidOperationException("Review models failed to load.");
GameObject trialPot=null;
object captured = null;''')
    source=source.replace('// The setter is a backing-field assignment in the recorded installed IL.', '''if(candidate)
        {
            west.Model=baseModel;
            trialPot=new GameObject(scene,false,"Temporary terracotta pot comparison");
            trialPot.Flags|=GameObjectFlags.NotSaved|GameObjectFlags.EditorOnly;
            trialPot.WorldPosition=new Vector3(514,1862,0);
            var renderer=trialPot.Components.Create<ModelRenderer>();
            renderer.Model=potModel;
            trialPot.Enabled=true;
        }
        // The setter is a backing-field assignment in the recorded installed IL.''')
    source=source.replace('var mainRestored = ReferenceEquals(scene.Camera, mainCamera);', '''using(scene.Push())
    {
        west.Model=westModel;
        if(trialPot.IsValid()) {trialPot.Destroy();scene.ProcessDeletes();}
    }
    var modelRestored=west.Serialize().ToJsonString()==westSerialized;
    var mainRestored = ReferenceEquals(scene.Camera, mainCamera);''')
    source=source.replace('ObjectsRestored = objectsRestored, EditorStatePreserved = statePreserved','ObjectsRestored = objectsRestored, ModelRestored=modelRestored, Candidate=candidate, EditorStatePreserved = statePreserved')
    source=source.replace('if (!mainRestored || !toneRestored || !camerasRestored || !objectsRestored || !statePreserved)','if (!modelRestored || !mainRestored || !toneRestored || !camerasRestored || !objectsRestored || !statePreserved)')
    destination=HERE/'capture.cs.txt'
    destination.write_text(source)
    return destination

def capture(name,candidate,position=(554,1934,34),target=(514,1862,17),fov=50):
    manifest=json.loads((OUT/'manifest.json').read_text())
    x,y,z=[b-a for a,b in zip(position,target)]
    angles=(math.degrees(math.atan2(-z,math.hypot(x,y))),math.degrees(math.atan2(y,x)),0)
    config={'directory':'review','name':name,'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),'width':1280,'height':1024,'fov':fov,'exposure':1.5,'settle_ms':0,'candidate':candidate,'expected_scene_sha256':manifest['guards']['Assets/scenes/maps/Belltower/belltower.scene']}
    (OUT/'capture.json').write_text(json.dumps(config))
    return script(prepare_capture(),name)

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='compile':
        for name in ('terracotta_pot','old_pot','west_without_one_pot'):
            print(name,json.dumps(call('asset_compile',{'path':f'models/maps/belltower/terracotta-pot-v2/{name}.vmdl'},'compile-'+name)))
    elif mode in ('before','after'):
        print(json.dumps(capture(mode,mode=='after'),indent=2))
    else:raise ValueError(mode)
