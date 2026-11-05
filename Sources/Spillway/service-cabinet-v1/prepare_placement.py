from pathlib import Path
import json
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent;out=root/'output/spillway/service-cabinet-v1'
s=(here/'context.cs.txt').read_text()
s=s.replace('        scene.Deserialize(root);','''        scene.Deserialize(root);
        // Inspection cutaway only: retain the Control collider, hide its stair
        // render mesh and add a work light to see the equipment below it.
        foreach(var r in scene.GetAllComponents<ModelRenderer>().Where(r=>r.GameObject.Name=="Control"))r.Enabled=false;
        var inspectionLight=new GameObject(true,"Temporary inspection light");
        inspectionLight.WorldPosition=new Vector3(285,290,100);
        var lamp=inspectionLight.Components.Create<PointLight>();lamp.LightColor=new Color(4,4,4);lamp.Radius=250;lamp.Shadows=false;''')
s=s.replace('Target: new Vector3(-302,345,40), Fov: 63f','Target: new Vector3(-302,345,40), Fov: 63f')
s=s.replace('view.Name + "-" + configuration["phase"].GetValue<string>() + ".png"','view.Name + "-placement-cutaway.png"')
(here/'placement.cs.txt').write_text(s)
p=out/'context/config.json';c=json.loads(p.read_text());c['phase']='installed';p.write_text(json.dumps(c,indent=2))
