"""Adapt the native isolated review workflow to the reused ladder."""
from pathlib import Path
HERE=Path(__file__).absolute().parent;ROOT=HERE.parents[2];OLD=HERE.parent/'water-tank-v1'
def rename(t):return t.replace('water-tank-v1','tower-ladder-v1').replace('water_tank_v1','tower_ladder_v1').replace('backdrop_without_tank','dressing_without_ladder').replace('legacy_tank','legacy_ladder').replace('tank_lod','ladder_lod').replace('tank.vmdl','ladder.vmdl')
code=rename((OLD/'import.cs.txt').read_text())
at='var session=Editor.SceneEditorSession.Active;'
code=code.replace(at,'''foreach(var pair in manifest["external_files"].AsObject())
    if(Hash(System.IO.Path.Combine(project,pair.Key))!=pair.Value.GetValue<string>())throw new Exception("Approved material changed: "+pair.Key);
'''+at)
(HERE/'import.cs.txt').write_text(code)
t=rename((OLD/'verify.py').read_text()).replace('<15000','<20000')
t=t.replace('reports=[]', '''for p,digest in manifest['external_files'].items():assert sha(ROOT/p)==digest,'Approved reused material changed: '+p
assert sha(ROOT/manifest['reused_approved_design'])==manifest['reused_recipe_sha']
reports=[]''')
(HERE/'verify.py').write_text(t)
t=rename((OLD/'review.py').read_text()).replace('import-tank','import-ladder').replace('capture-tank','capture-ladder')
a=t.index('var key=new SceneLight');b=t.index('            var pixmap=',a)
t=t[:a]+'''var key=new SceneLight(world,new Vector3(-160,-130,560),1300,Color.White*12f);
        var fill=new SceneLight(world,new Vector3(200,200,200),1300,new Color(.75f,.85f,1f)*18f);
        foreach(var (name,eye) in new[]{("overview",new Vector3(-650,-700,420)),("detail",new Vector3(-160,-115,536)),("treads",new Vector3(-35,-36,250))})
        {
            var aim=name=="detail"?new Vector3(25,0,530):name=="treads"?new Vector3(10,0,254):new Vector3(12,0,280);
            var camera=new SceneCamera("Fitted approved ladder review") { World=world,Position=eye,Rotation=Rotation.LookAt(aim-eye),
                FieldOfView=name=="overview"?50:48,ZNear=.1f,ZFar=5000,Size=new Vector2(1200,900),AmbientLightColor=Color.White*.24f,
                BackgroundColor=new Color(.055f,.065f,.075f),AntiAliasing=true,EnablePostProcessing=true};
'''+t[b:]
(HERE/'review.py').write_text(t)
code=rename((OLD/'context.cs.txt').read_text()).replace('models/maps/riverside/riverside_backdrop.vmdl','models/maps/riverside/riverside_dressing.vmdl')
code=code.replace('"Water Tower Tanks"','"Water Tower Tanks"')
# Include every saved model-bearing visual root, including concurrent approved prop groups.
code=code.replace('foreach (var item in root["GameObjects"].AsArray())','''bool HasModels(System.Text.Json.Nodes.JsonNode item)=>
    (item["Components"]?.AsArray().Any(c=>c?["__type"]?.GetValue<string>()=="Sandbox.ModelRenderer")??false)
    ||(item["Children"]?.AsArray().Any(c=>c is not null&&HasModels(c))??false);
foreach (var item in root["GameObjects"].AsArray())''')
code=code.replace('if (visual.Contains(item["Name"]?.GetValue<string>() ?? ""))','if (visual.Contains(item["Name"]?.GetValue<string>() ?? "") || HasModels(item))')
a=code.index('var at=new Vector3');b=code.index('\nvar scene = ',a)
code=code[:a]+'''var folder=System.IO.Path.Combine(projectRoot,"output/riverside/tower-ladder-v1");
var manifest=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"manifest.json")));
var p=manifest["position"].AsArray();var at=new Vector3(p[0].GetValue<float>(),p[1].GetValue<float>(),p[2].GetValue<float>());
var rotation=Rotation.FromYaw(manifest["yaw"].GetValue<float>());
Vector3 Local(float x,float y,float z)=>at+rotation*new Vector3(x,y,z);
var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("upper",Local(-150,-130,555),Local(25,0,525),50f,true),
    ("tower",Local(-1000,-300,350),Local(10,0,288),50f,true)
};
'''+code[b:]
code=code.replace('newObject.WorldPosition=at;', 'newObject.WorldPosition=at;newObject.WorldRotation=rotation;')
(HERE/'context.cs.txt').write_text(code)
print('Reused ladder review scripts prepared')
