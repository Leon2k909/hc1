from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=(ROOT/'Sources/Orion/yard-lamp-v1/capture.cs.txt').read_text()
s=s.replace('output/orion/yard-lamp-v1','Sources/ReefHall/bronze-planter-v1/review')
s=s.replace('models/maps/orion/yard-lamp-v1/','models/maps/reefhall/bronze-planter-v1/')
s=s.replace('"before","lamp"','"before","planter"').replace('Yard lamp head comparison','Bronze planter comparison')
s=s.replace('new Vector3(0,0,-12.2f)','new Vector3(0,0,-.2f)')
s=s.replace('W(15,-50,85)','W(45,-65,100)').replace('W(18,-32,-8)','W(65,-95,80)').replace('W(0,0,-3)','W(0,0,36)').replace('FieldOfView=34','FieldOfView=40')
(HERE/'capture.cs.txt').write_text(s)
s=(ROOT/'Sources/Orion/yard-lamp-v1/context.cs.txt').read_text()
s=s.replace('output/orion/yard-lamp-v1/context','Sources/ReefHall/bronze-planter-v1/review/context').replace('Assets/scenes/maps/Orion/orion.scene','Assets/scenes/maps/ReefHall/reefhall.scene')
s=s.replace('{"Sun","Sky","Fog","Look","Orion","Lights","Reflection Probes"}','{"Ambient","Fog","Aquarium","Lights","Reflection Probes"}')
s=s.replace('scene.Deserialize(root);','''scene.Deserialize(root);
        foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/reefhall/reefhall_lobby.vmdl")) {
            renderer.Model=Model.Load("models/maps/reefhall/bronze-planter-v1/lobby_preview.vmdl");
            if(renderer.Model.IsError)throw new InvalidOperationException("Lobby preview error");
        }
''')
s=s.replace('(Name: "fixture", Eye: new Vector3(215f,116f,74f), Target: new Vector3(181f,166f,95f), Fov: 37f)',
 '(Name: "fixture", Eye: new Vector3(-2775f,-180f,75f), Target: new Vector3(-2885.56f,-98.75f,37f), Fov: 48f)')
s=s.replace('(Name: "location", Eye: new Vector3(120f,65f,72f), Target: new Vector3(181f,166f,50f), Fov: 75f)',
 '(Name: "location", Eye: new Vector3(-2580f,-250f,100f), Target: new Vector3(-2890f,0f,70f), Fov: 82f)')
s=s.replace('g.Parent.Name == "Orion"','g.Parent.Name == "Aquarium"')
(HERE/'context.cs.txt').write_text(s)
context=HERE/'review/context';context.mkdir(parents=True,exist_ok=True)
(context/'config.json').write_text('{"phase":"preview","width":1600,"height":1000,"stream_frames":65,"settle_frames":30}')
