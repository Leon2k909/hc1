from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/capture.cs.txt').read_text()
s=s.replace('Sources/ReefHall/bronze-planter-v1/review','Sources/Spillway/roof-fans-v1/review')
s=s.replace('models/maps/reefhall/bronze-planter-v1/','models/maps/spillway/roof-fans-v1/')
s=s.replace('"before","planter"','"before","fan"').replace('Bronze planter comparison','Rooftop extractor comparison')
s=s.replace('W(65,-95,80)','W(105,-125,125)').replace('W(0,0,36)','W(0,0,4)').replace('FieldOfView=40','FieldOfView=45')
s=s.replace('W(45,-65,100)','W(30,-65,140)')
s=s.replace('1000,1150','1200,900').replace('FieldOfView=45','FieldOfView=34')
(HERE/'capture.cs.txt').write_text(s)
s=(ROOT/'Sources/Orion/yard-lamp-v1/context.cs.txt').read_text()
s=s.replace('output/orion/yard-lamp-v1/context','Sources/Spillway/roof-fans-v1/review/context').replace('Assets/scenes/maps/Orion/orion.scene','Assets/scenes/maps/Spillway/spillway.scene')
s=s.replace('{"Sun","Sky","Fog","Look","Orion","Lights","Reflection Probes"}','{"Sun","Sky","Fog","Look","Spillway","Lights","Reflection Probes","Sky Fill","Spillway indirect light"}')
s=s.replace('scene.Deserialize(root);','''scene.Deserialize(root);
        var swapped=0;
        foreach(var name in new[]{"spillway_west","spillway_east"})
         foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/spillway/"+name+".vmdl")) {
            renderer.Model=Model.Load("models/maps/spillway/roof-fans-v1/"+name+"_preview.vmdl");
            if(renderer.Model.IsError)throw new InvalidOperationException("Fan preview error");
            swapped++;
        }
        if(swapped!=2)throw new InvalidOperationException("Expected two roof model substitutions");
''')
s=s.replace('(Name: "fixture", Eye: new Vector3(215f,116f,74f), Target: new Vector3(181f,166f,95f), Fov: 37f)',
 '(Name: "fixture", Eye: new Vector3(-1810f,255f,865f), Target: new Vector3(-1940f,440f,716f), Fov: 55f)')
s=s.replace('(Name: "location", Eye: new Vector3(120f,65f,72f), Target: new Vector3(181f,166f,50f), Fov: 75f)',
 '(Name: "location", Eye: new Vector3(-2550f,-110f,1100f), Target: new Vector3(-1930f,650f,425f), Fov: 70f),\n        (Name: "tower", Eye: new Vector3(1550f,-30f,1260f), Target: new Vector3(1985f,200f,1070f), Fov: 75f)')
s=s.replace('g.Parent.Name == "Orion"','g.Parent.Name == "Spillway"')
(HERE/'context.cs.txt').write_text(s)
context=HERE/'review/context';context.mkdir(parents=True,exist_ok=True)
(context/'config.json').write_text('{"phase":"preview","width":1600,"height":1000,"stream_frames":65,"settle_frames":30}')
s=(ROOT/'Sources/ReefHall/bronze-planter-v1/compile.py').read_text().replace("('before','planter','lobby_preview')","('before','fan','spillway_west_preview','spillway_east_preview')").replace('models/maps/reefhall/bronze-planter-v1/','models/maps/spillway/roof-fans-v1/')
(HERE/'compile.py').write_text(s)
