"""Prepare native-editor scripts and the water shader. Does not modify live assets."""
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"Sources/Spillway"
EDITOR=SOURCE/"editor"
OUT=ROOT/"output/spillway"
EDITOR.mkdir(parents=True,exist_ok=True)
(SOURCE/"shaders").mkdir(parents=True,exist_ok=True)
(SOURCE/"shaders/hc1_spillway_mountain_v4.shader").write_text((SOURCE/"shaders/hc1_spillway_mountain.shader").read_text().replace('    Depth( S_MODE_DEPTH );','    Depth( S_MODE_DEPTH );\n    ToolsShadingComplexity( "tools_shading_complexity.shader" );'))

river=(ROOT/"Assets/shaders/hc1_lowtide_water.shader").read_text()
river=river.replace('Description = "Lowtide tidal water: moving ripples, reflected light and shallow-bank transparency";',
                    'Description = "Spillway tailrace: running alpine water, turbulent eddies and advected whitewater";')
noise='''    float SWHash( float2 p ) { return frac( sin( dot(p,float2(127.1,311.7)) )*43758.5453 ); }
    float SWNoise( float2 p )
    {
        float2 a=floor(p), f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(SWHash(a),SWHash(a+float2(1,0)),f.x),lerp(SWHash(a+float2(0,1)),SWHash(a+1),f.x),f.y);
    }

'''
river=river.replace('    float4 MainPs( PixelInput input )',noise+'    float4 MainPs( PixelInput input )')
river=river.replace('        CombinerInput lightingInput', '''        float2 swp = position / float2(140,85);
        float swWarp = SWNoise(swp*.43 + g_flTime*.06);
        float swNoise = SWNoise(swp + swWarp*3)*.65 + SWNoise(swp*2.4 + swWarp*5)*.35;
        float swFoam = smoothstep(.54,.74,swNoise) * .92;
        water.Albedo = lerp(water.Albedo,float3(.61,.72,.75),swFoam);
        water.Roughness = lerp(water.Roughness,.48,swFoam);
        water.Opacity = lerp(water.Opacity,1,swFoam);

        CombinerInput lightingInput''')
(SOURCE/"shaders/hc1_spillway_river.shader").write_text(river)
(SOURCE/"shaders/hc1_spillway_river_v2.shader").write_text(river.replace('position / float2(140,85)','position / float2(88,37)').replace('smoothstep(.54,.74,swNoise) * .92','smoothstep(.64,.79,swNoise) * .32').replace('float3(.61,.72,.75)','float3(.27,.30,.31)'))
(SOURCE/"shaders/hc1_spillway_falls_v2.shader").write_text((SOURCE/"shaders/hc1_spillway_falls.shader").read_text().replace('m.Albedo * .10','m.Albedo * .30'))
falls=(SOURCE/"shaders/hc1_spillway_falls.shader").read_text()
falls=falls.replace('Range( 0, 1 )','Range( 0, 2 )').replace('float3(.21,.30,.34), float3(.83,.89,.91)','float3(.30,.39,.43), float3(.66,.73,.77)')
falls=falls.replace('m.Albedo * .10','m.Albedo * .12')
falls=falls.replace('        return ShadingModelStandard::Shade( m );','''        if (g_flFoam > 1.5)
        {
            float2 q=(uv-.5)*2;
            float cloud=Noise(uv*4+float2(t*.06,0))*.65+Noise(uv*9-float2(0,t*.03))*.35;
            float rim=saturate(1-dot(q,q));
            m.Albedo=float3(.63,.70,.74);m.Emission=m.Albedo*.2;
            m.Opacity=rim*rim*smoothstep(.15,.60,cloud)*.25;
            m.Roughness=1;
        }
        return ShadingModelStandard::Shade( i, m );''')
(SOURCE/"shaders/hc1_spillway_falls_v3.shader").write_text(falls)
materials=OUT/"stage/materials/spillway"
for name,shader in (("sw_fall","falls"),("sw_foam","falls"),("sw_river","river")):
    text=(materials/(name+".vmat")).read_text().replace('hc1_spillway_'+shader+'.shader','hc1_spillway_'+shader+'_v2.shader')
    if name=="sw_river":text=text.replace('"83"','"34"').replace('"1.35"','"0.80"').replace('[0.036 0.094 0.105]','[0.018 0.042 0.047]')
    (materials/(name+"_v2.vmat")).write_text(text)
for name,foam in (("sw_fall",0),("sw_foam",1),("sw_mist",2)):
    (materials/(name+"_v3.vmat")).write_text('"Layer0"\n{\n shader "shaders/hc1_spillway_falls_v3.shader"\n g_flFoam "'+str(foam)+'"\n}\n')
for name in ("sw_concrete","sw_dam","sw_trim","sw_yard","sw_mountain","sw_hill"):
    path=materials/(name+".vmat")
    mat=path.read_text().replace('shaders/complex.shader','shaders/hc1_spillway_mountain.shader' if name in ("sw_mountain","sw_hill") else 'shaders/hc1_spillway_concrete.shader')
    mat=mat.replace('g_vColorTint','g_flTintColor')
    if name=="sw_dam":
        mat=re.sub(r'\s+g_flWearScale\s+"[^"]*"','',mat)
        mat=mat.replace('\n}', '\n    g_flWearScale "3.0"\n}')
    path.write_text(mat)
    if name in ("sw_mountain","sw_hill"):
        (materials/(name+"_v3.vmat")).write_text(mat.replace('hc1_spillway_mountain.shader','hc1_spillway_mountain_v4.shader'))

imports=(ROOT/"Sources/Sewage/editor/import-assets.cs.txt").read_text().replace('sewage','spillway').replace('Sewage','Spillway')
imports=imports.replace('if (Game.IsPlaying) throw new InvalidOperationException("Stop play before importing the new map assets.");', '''if (Game.IsPlaying && Game.ActiveScene?.Source?.ResourcePath?.Contains("/spillway/",StringComparison.OrdinalIgnoreCase)==true)
    throw new InvalidOperationException("Stop Spillway before importing its assets.");''')
imports=imports.replace('!relative.StartsWith("sounds/spillway/")','!relative.StartsWith("sounds/spillway/") && !relative.StartsWith("ui/minimaps/minimap_spillway") && !relative.StartsWith("ui/maps/spillway")')
imports=imports.replace('await Editor.EditorUtility.CompileShader(relative,new(),cancellationToken);','var result=await Editor.EditorUtility.CompileShader(relative,new(){ForceRecompile=true},cancellationToken);\n    if(!result.Success) throw new InvalidOperationException("Shader compile failed: "+relative);\n    if(result.CompiledShader is {Length:>0}) System.IO.File.WriteAllBytes(destination+"_c",result.CompiledShader);')
(EDITOR/"import-assets.cs.txt").write_text(imports)
assemble=(ROOT/"Sources/Sewage/editor/import-scene.cs.txt").read_text().replace('sewage','spillway').replace('Sewage','Spillway')
assemble=assemble.replace('if(Game.IsPlaying) throw new InvalidOperationException("Stop play before assembling the scene.");\n','')
assemble=assemble.replace('const string relative="scenes/maps/spillway/spillway.scene";', '''const string relative="scenes/maps/spillway/spillway.scene";
if(Game.IsPlaying && Game.ActiveScene?.Source?.ResourcePath?.Equals(relative,StringComparison.OrdinalIgnoreCase)==true)
    throw new InvalidOperationException("Stop the running Spillway match before updating its scene resource.");''')
(EDITOR/"import-scene.cs.txt").write_text(assemble)

capture=(ROOT/"Sources/Riverdale/editor/capture.cs.txt").read_text().replace('riverdale','spillway').replace('Riverdale','Spillway')
capture=capture.replace('"Sun", "Sky", "Fog", "Look",','"Sun", "Sky", "Sky Fill", "Fog", "Look",')
capture=capture.replace('        foreach (var probe in scene.GetAllComponents<EnvmapProbe>()) probe.Mode = EnvmapProbe.EnvmapProbeMode.Realtime;\n','')
probe_start=capture.index('    var renderProbe = ')
probe_end=capture.index('    // Plan ',probe_start)
capture=capture[:probe_start]+capture[probe_end:]
capture=capture.replace('camera.ZNear = 4;', 'camera.CustomSize = new Vector2(configuration["width"]?.GetValue<int>() ?? 1600, configuration["height"]?.GetValue<int>() ?? 1000);\n        camera.ZNear = 4;')
capture=capture.replace('                camera.RenderToBitmap(bitmap);', '                camera.CustomSize = new Vector2(configuration["width"]?.GetValue<int>() ?? 1600, configuration["height"]?.GetValue<int>() ?? 1000);\n                camera.RenderToBitmap(bitmap);')
start=capture.index('    var views = new[] {')
end=capture.index('    var wanted = ',start)
capture=capture[:start]+'''    var views = new[] {
        (Name: "reference", Eye: new Vector3(1100,-3100,700), Target: new Vector3(-100,850,620), Fov: 78f),
        (Name: "reference_west", Eye: new Vector3(-1350,-3270,700), Target: new Vector3(360,850,620), Fov: 78f),
        (Name: "cargo", Eye: new Vector3(-420,-1020,70), Target: new Vector3(120,800,215), Fov: 86f),
        (Name: "b2", Eye: new Vector3(1600,-1630,200), Target: new Vector3(-550,1200,500), Fov: 86f),
        (Name: "turbine", Eye: new Vector3(-1120,-500,70), Target: new Vector3(-1550,800,320), Fov: 84f),
        (Name: "control", Eye: new Vector3(100,1120,300), Target: new Vector3(0,-700,200), Fov: 84f),
        (Name: "aerial", Eye: new Vector3(-3700,-4200,4500), Target: new Vector3(0,100,100), Fov: 65f),
        (Name: "dam", Eye: new Vector3(-800,1600,300), Target: new Vector3(-2300,4400,1900), Fov: 82f),
        (Name: "red_spawn", Eye: new Vector3(-2080,-1450,64), Target: new Vector3(-1350,-1050,65), Fov: 85f),
        (Name: "blue_spawn", Eye: new Vector3(2150,-1400,192), Target: new Vector3(1550,-1200,192), Fov: 85f),
    };
'''+capture[end:]
(EDITOR/"capture.cs.txt").write_text(capture)
validate=(ROOT/"Sources/Collider/editor/validate-map.cs.txt").read_text().replace('collider','spillway').replace('Collider','Spillway')
(EDITOR/"validate-map.cs.txt").write_text(validate)
isolated='''var root=Sandbox.Project.Current.GetRootPath();
var before=Editor.SceneEditorSession.Active?.Scene?.Id;
var scene=Scene.CreateEditorScene();
try {
var json=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"Assets/scenes/maps/spillway/spillway.scene"))).AsObject();
var keep=new[]{"Spillway","Player Clips","Catch Floor"};
var roots=new System.Text.Json.Nodes.JsonArray();
foreach(var item in json["GameObjects"].AsArray()) if(keep.Contains(item["Name"]?.GetValue<string>()))roots.Add(item.DeepClone());
json["GameObjects"]=roots;
json["SceneProperties"]["WantsSystemScene"]=false;
json["SceneProperties"]["NavMesh"]["EditorAutoUpdate"]=false;
using(scene.Push()){scene.Deserialize(json);scene.EditorTick(.016f,.016f);}
Task<bool> build;
using(scene.Push())build=scene.NavMesh.Generate(scene.PhysicsWorld);
if(!await build)throw new InvalidOperationException("Navigation generation failed");
'''
body=validate[validate.index('var requested='):]
body=body.replace('scene.Source.ResourcePath','"scenes/maps/spillway/spillway.scene"')
body=body.replace('Facepunch.GameMode.GetAll((SceneFile)scene.Source)','Facepunch.GameMode.GetAll(Editor.AssetSystem.FindByPath("scenes/maps/spillway/spillway.scene").LoadResource<SceneFile>())')
body=body.replace('var models=', '''Vector3 World(Vector3 p)=>new(p.y,-p.x,p.z);
var stairPairs=new[] {
    (Name:"Control west stair",Start:new Vector3(-275,145,0),End:new Vector3(-275,720,236)),
    (Name:"Control east stair",Start:new Vector3(560,145,0),End:new Vector3(560,720,236)),
    (Name:"B2 west stair",Start:new Vector3(1130,-1320,0),End:new Vector3(1500,-1320,128)),
    (Name:"B2 north stair",Start:new Vector3(1515,-480,0),End:new Vector3(1515,-870,128))
};
var stairs=stairPairs.Select(pair=>{
    var start=scene.NavMesh.GetClosestPoint(World(pair.Start),48);
    var end=scene.NavMesh.GetClosestPoint(World(pair.End),48);
    if(start is null || end is null)return new {pair.Name,Status="MissingNavMesh",Length=0f,Direct=false};
    var route=scene.NavMesh.CalculatePath(new Sandbox.Navigation.CalculatePathRequest{Start=start.Value,Target=end.Value});
    var points=route.Points.Select(x=>x.Position).ToArray();
    var length=points.Zip(points.Skip(1),(a,b)=>a.Distance(b)).Sum();
    return new {pair.Name,Status=route.Status.ToString(),Length=length,Direct=route.Status.ToString()=="Complete" && length<(pair.End-pair.Start).Length*1.55f};
}).ToArray();
var models=''')
body=body.replace('MissingModels=missingModels, MissingMaterials=missingMaterials,','MissingModels=missingModels, MissingMaterials=missingMaterials, Stairs=stairs,')
body=body.replace('result.Failed, result.NavEnabled','result.Failed, result.Stairs, result.NavEnabled')
isolated+=body+'\n}finally{scene.Destroy();}\n'
(EDITOR/"validate-isolated.cs.txt").write_text(isolated)
(EDITOR/"compile-assets.cs.txt").write_text((ROOT/"Sources/Riverdale/editor/compile-stale.cs.txt").read_text().replace('riverdale','spillway').replace('Riverdale','Spillway'))
for name in ("prepare-live-round","check-live-round","restore-test-settings"):
    script=(ROOT/("Sources/Collider/editor/"+name+".cs.txt")).read_text().replace('collider','spillway').replace('Collider','Spillway')
    if name=="prepare-live-round":
        script=script.replace('var previous=new { NoDamage=', 'var previous=new { EditorLobby=Facepunch.GameNetworkManager.EditorLobby,NoDamage=')
        script=script.replace('Facepunch.DevCommands.NoDamage=true;', 'Facepunch.DevCommands.NoDamage=true;\nFacepunch.GameNetworkManager.EditorLobby=false;')
    if name=="restore-test-settings":
        script=script.replace('Facepunch.DevCommands.NoDamage=previous', 'Facepunch.GameNetworkManager.EditorLobby=previous["EditorLobby"].GetValue<bool>();\nFacepunch.DevCommands.NoDamage=previous')
    if name=="check-live-round":
        script=script.replace('    Networking.IsActive,', '    Reflections=scene.GetAllComponents<EnvmapProbe>().Select(p=>new {Name=p.GameObject.Name,Mode=p.Mode.ToString(),Texture=p.Texture?.ResourcePath,Valid=p.Texture is not null && !p.Texture.IsError}).ToArray(),\n    Networking.IsActive,')
    (EDITOR/(name+".cs.txt")).write_text(script)
(OUT/"captures").mkdir(parents=True,exist_ok=True)
(OUT/"captures/config.json").write_text(json.dumps({"views":["reference"],"width":1600,"height":1000,"settle_frames":12,"stream_frames":45},indent=2))
print("Prepared editor scripts and moving river shader in Sources/Spillway.")
from spillway_realism import stage_materials
stage_materials()
