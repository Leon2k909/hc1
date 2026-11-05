from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/crane-blocks-v1/demonstration';OUT.mkdir(exist_ok=True)
script=(HERE/'context.cs.txt').read_text().replace('output/sewage/crane-blocks-v1/context','output/sewage/crane-blocks-v1/demonstration')
script=script.replace('        scene.Deserialize(root);','''        scene.Deserialize(root);
        foreach(var item in new[]{new Vector3(600,-300,900),new Vector3(730,400,850)}) {
            var fill=new GameObject(true,"Temporary inspection fill");
            fill.WorldPosition=new Vector3(item.y,-item.x,item.z);
            var light=fill.Components.Create<PointLight>();light.LightColor=new Color(5f,4.8f,4.4f);
            light.Radius=1200;light.Shadows=false;
        }
''')
script=script.replace('camera.ZNear = 4;','camera.FovAxis=CameraComponent.Axis.Horizontal;camera.EnablePostProcessing=true;\n        camera.ZNear = 4;')
start=script.index('    var views = new[] {');end=script.index('    var wanted =',start)
script=script[:start]+'''    var views = new[] {
        (Name: "location", Eye: new Vector3(700f,-850f,520f), Target: new Vector3(470f,240f,670f), Fov: 85f),
        (Name: "mounting", Eye: new Vector3(800f,-430f,930f), Target: new Vector3(610f,-20f,840f), Fov: 70f),
        (Name: "catwalk", Eye: new Vector3(860f,-320f,608f), Target: new Vector3(610f,-20f,780f), Fov: 78f),
    };
'''+script[end:]
script=script.replace('        cancellationToken.ThrowIfCancellationRequested();\n        for (var frame', '''        cancellationToken.ThrowIfCancellationRequested();
        foreach(var light in scene.GetAllComponents<PointLight>().Where(l=>l.GameObject.Name=="Temporary inspection fill"))light.GameObject.Enabled=view.Name!="catwalk";
        for (var frame''')
(HERE/'demonstration.cs.txt').write_text(script)
(OUT/'config.json').write_text(json.dumps(dict(phase='view',width=1920,height=1200,settle_frames=35,stream_frames=40),indent=2))
protected=['Assets/scenes/maps/sewage/sewage.scene','Assets/models/maps/sewage/sewage_details.obj','Assets/models/maps/sewage/sewage_details.vmdl']
(OUT/'protected-hashes.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in protected},indent=2))
