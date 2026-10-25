using Editor;
using Sandbox;
using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Repeatable isolated engine views and collision checks, without changing the open editor scene.</summary>
public static class Hc1ForestBaseQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/forestbase" );
	private static bool running;
	private static readonly System.Collections.Generic.List<CameraComponent> inspectionHiddenCameras=new();
	private static readonly System.Collections.Generic.List<(Facepunch.TeamEarlyWinCondition condition,int score)> inspectionScores=new();
	private static Vector3 Plan( float e, float n, float z ) => new( n, -e, z );
	[ConCmd("hc1_forestbase_perfview")]
	public static void PerfView(int view=0)
	{
		var scene=Game.ActiveScene;
		if(scene==null || scene.Name!="forestbase")return;
		using(scene.Push())
		{
			foreach(var previous in scene.GetAllObjects(true).Where(x=>x.Name=="Forest Base performance camera").ToArray())previous.Destroy();
			if(view<0)
			{
				foreach(var previous in inspectionHiddenCameras.Where(x=>x.IsValid()))previous.IsMainCamera=true;
				foreach(var previous in inspectionScores.Where(x=>x.condition.IsValid()))previous.condition.TargetScore=previous.score;
				inspectionScores.Clear();
				inspectionHiddenCameras.Clear();return;
			}
			foreach(var limit in scene.GetAllComponents<Facepunch.TeamEarlyWinCondition>())
			{
				if(!inspectionScores.Any(x=>x.condition==limit))inspectionScores.Add((limit,limit.TargetScore));
				limit.TargetScore=10000;
			}
			foreach(var previous in scene.GetAllComponents<CameraComponent>().Where(x=>x.IsMainCamera))
			{
				inspectionHiddenCameras.Add(previous);previous.IsMainCamera=false;
			}
			var go=new GameObject(true,"Forest Base performance camera");
			var camera=go.Components.Create<CameraComponent>();
			camera.IsMainCamera=true;camera.Priority=100;camera.FieldOfView=85;camera.ZFar=18000;
			var ao=go.Components.Create<AmbientOcclusion>();ao.Intensity=.15f;ao.Radius=128;ao.FalloffRange=.75f;
			var bloom=go.Components.Create<Bloom>();bloom.Strength=.15f;bloom.Threshold=1.33f;
			var eye=view==0?Plan(-200,-1180,68):view==1?Plan(540,740,448):view==3?Plan(500,1080,448):view==4?Plan(-120,-1660,68):Plan(-1400,-180,180);
			var target=view==0?Plan(250,900,200):view==1?Plan(500,-80,64):view==3?Plan(410,3230,830):view==4?Plan(0,-2300,-240):Plan(-2000,350,450);
			go.WorldPosition=eye;go.WorldRotation=Rotation.LookAt(target-eye);
		}
	}
	[ConCmd("hc1_forestbase_perfcapture")]
	public static void PerfCapture()
	{
		var scene=Game.ActiveScene;
		var camera=scene?.GetAllComponents<CameraComponent>().FirstOrDefault(x=>x.GameObject.Name=="Forest Base performance camera");
		if(camera==null)return;
		using var bitmap=new Bitmap(1600,900);
		using(scene.Push())camera.RenderToBitmap(bitmap,false);
		File.WriteAllBytes(Path.Combine(Folder,"live-perf-view.png"),bitmap.ToPng());
		Log.Info($"Forest Base perf camera: {camera.WorldPosition}, SSR volumes {scene.GetAllComponents<ScreenSpaceReflections>().Count()}");
	}
	[ConCmd("hc1_forestbase_flowcapture")]
	public static async void FlowCapture(string prefix="flow")
	{
		if(string.IsNullOrWhiteSpace(prefix)||prefix.Any(x=>!char.IsLetterOrDigit(x)&&x!='-'))return;
		var scene=Game.ActiveScene;
		var camera=scene?.GetAllComponents<CameraComponent>().FirstOrDefault(x=>x.GameObject.Name=="Forest Base performance camera");
		if(!Game.IsPlaying||camera==null)return;
		var captures=new System.Collections.Generic.List<object>();
		using var bitmap=new Bitmap(1600,900);
		for(var frame=0;frame<3;frame++)
		{
			if(!scene.IsValid()||!camera.IsValid())return;
			using(scene.Push())camera.RenderToBitmap(bitmap,false);
			var stamp=DateTime.UtcNow;
			var file=$"{prefix}-runtime-waterfall-{frame}.png";
			File.WriteAllBytes(Path.Combine(Folder,file),bitmap.ToPng());
			captures.Add(new{file,utc=stamp.ToString("O"),cameraPosition=camera.WorldPosition.ToString()});
			if(frame<2)await Task.Delay(200);
		}
		File.WriteAllText(Path.Combine(Folder,$"{prefix}-runtime-captures.json"),JsonSerializer.Serialize(captures,new JsonSerializerOptions{WriteIndented=true}));
		Log.Info("Forest Base timed waterfall captures complete.");
	}
	[ConCmd("hc1_forestbase_postschema")]
	public static void PostSchema()
	{
		var types=new[]{"Sandbox.PostProcessVolume","Sandbox.ScreenSpaceReflections","Sandbox.AmbientOcclusion","Sandbox.CameraComponent","Sandbox.VolumetricFogVolume","Sandbox.VolumetricFog","Sandbox.Tonemapping","Sandbox.SpotLight"};
		var report=types.Where(t=>Game.TypeLibrary.GetType(t)!=null).Select(t=>new { type=t, properties=Game.TypeLibrary.GetType(t).Properties.Select(p=>new{name=p.Name,type=p.PropertyType.FullName}).ToArray() }).ToArray();
		File.WriteAllText(Path.Combine(Folder,"post-schema.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
		var scene=new Scene();
		using(scene.Push())
		{
			var go=new GameObject(true,"Global effects schema");
			go.Components.Create<PostProcessVolume>().SceneVolume=new Sandbox.Volumes.SceneVolume{Type=Sandbox.Volumes.SceneVolume.VolumeTypes.Infinite};
			go.Components.Create<Tonemapping>();
			File.WriteAllText(Path.Combine(Folder,"post-volume-serialization.json"),go.Serialize().ToJsonString(new JsonSerializerOptions{WriteIndented=true,TypeInfoResolver=JsonSerializerOptions.Default.TypeInfoResolver}));
			var fog=new GameObject(true,"Volumetric fog schema");
			fog.Components.Create<VolumetricFogVolume>();
			File.WriteAllText(Path.Combine(Folder,"fog-volume-serialization.json"),fog.Serialize().ToJsonString(new JsonSerializerOptions{WriteIndented=true,TypeInfoResolver=JsonSerializerOptions.Default.TypeInfoResolver}));
		}
		scene.Destroy();
	}
	[ConCmd("hc1_forestbase_perfcontext")]
	public static void PerfContext()
	{
		var scene=Game.ActiveScene;
		if(!Game.IsPlaying||scene?.Name!="forestbase")return;
		var report=new {
			utc=DateTime.UtcNow.ToString("O"),scene=scene.Name,mode=Facepunch.GameMode.Instance?.Ident,
			screen=Sandbox.Screen.Size.ToString(),
			modelRenderers=scene.GetAllComponents<ModelRenderer>().Count(),
			modelErrors=scene.GetAllComponents<ModelRenderer>().Count(x=>x.Model==null||x.Model.IsError),
			ssrVolumes=scene.GetAllComponents<ScreenSpaceReflections>().Count(),
			cameras=scene.GetAllComponents<CameraComponent>().Select(x=>new { name=x.GameObject.Name,x.IsMainCamera,x.Priority,position=x.WorldPosition.ToString() }).ToArray()
		};
		File.WriteAllText(Path.Combine(Folder,"runtime-context.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions { WriteIndented=true }));
		Log.Info($"Forest Base runtime context: screen {Sandbox.Screen.Size}, SSR {report.ssrVolumes}, cameras {report.cameras.Length}, models {report.modelRenderers}");
	}
	[ConCmd("hc1_forestbase_lightpreview")]
	public static async void LightPreview()
	{
		var scene=new Scene();
		try
		{
			var root=JsonNode.Parse(File.ReadAllText(Path.Combine(Project.Current.GetRootPath(),"Assets/scenes/maps/ForestBase/forestbase.scene"))).AsObject();
			var objects=new JsonArray();
			foreach(var item in root["GameObjects"].AsArray())
				if(new[]{"Military Outpost","Forest Backdrop","Cool Daylight","Sky","Forest Mist","Warm Military Lights","Reflections","Rain Reflections"}.Contains(item["Name"]?.GetValue<string>()))objects.Add(item.DeepClone());
			root["GameObjects"]=objects;root["SceneProperties"]["NavMesh"]["Enabled"]=false;root["SceneProperties"]["WantsSystemScene"]=false;
			CameraComponent camera;
			using(scene.Push())
			{
				scene.Deserialize(root);
				camera=new GameObject(true,"Lighting diagnostic camera").Components.Create<CameraComponent>();
				camera.FieldOfView=72;camera.ZNear=1;camera.ZFar=18000;
				var ao=camera.GameObject.Components.Create<AmbientOcclusion>();ao.Intensity=.15f;ao.Radius=128;ao.FalloffRange=.75f;
				foreach(var tone in scene.GetAllComponents<Tonemapping>()) { tone.MinimumExposure=1;tone.MaximumExposure=1; }
				scene.EditorTick(.016f,.016f);
			}
			await Task.Delay(1000);
			var compound=scene.GetAllComponents<VolumetricFogVolume>().Single(x=>x.GameObject.Name=="Illuminated compound air");
			var backdrop=scene.GetAllComponents<VolumetricFogVolume>().Single(x=>x.GameObject.Name=="Forest atmospheric depth");
			var results=new System.Collections.Generic.List<object>();
			using var bitmap=new Bitmap(1600,900);
			for(var profile=0;profile<3;profile++)
			{
				compound.Strength=profile==0?.012f:profile==1?.06f:.12f;
				backdrop.Strength=profile==0?.075f:profile==1?.25f:.5f;
				foreach(var view in new[]{("aerial",Plan(-2600,-2900,2000),Plan(0,200,90)),("entrance",Plan(0,-1680,68),Plan(50,900,260))})
				{
					using(scene.Push())
					{
						camera.WorldPosition=view.Item2;camera.WorldRotation=Rotation.LookAt(view.Item3-view.Item2);
						scene.EditorTick(1,.016f);camera.RenderToBitmap(bitmap,false);
						using var parameters=new SceneCamera("Fog settings inspection");camera.UpdateSceneCamera(parameters);
						results.Add(new{profile,view=view.Item1,compound=compound.Strength,backdrop=backdrop.Strength,
							fogEnabled=parameters.VolumetricFog.Enabled,scattering=parameters.VolumetricFog.Scattering,drawDistance=parameters.VolumetricFog.DrawDistance});
					}
					File.WriteAllBytes(Path.Combine(Folder,$"light-diagnostic-{profile}-{view.Item1}.png"),bitmap.ToPng());
					await Task.Delay(200);
				}
			}
			File.WriteAllText(Path.Combine(Folder,"light-diagnostic.json"),JsonSerializer.Serialize(results,new JsonSerializerOptions{WriteIndented=true}));
			Log.Info("Forest Base lighting diagnostic complete; fixed exposure 1, three fog densities.");
		}
		finally { scene.Destroy(); }
	}
	[ConCmd( "hc1_forestbase_treeqa" )]
	public static async void Trees()
	{
		Directory.CreateDirectory(Folder);
		var scene=new Scene();
		try
		{
			CameraComponent camera;
			var report=new System.Collections.Generic.List<object>();
			using(scene.Push())
			{
				camera=new GameObject(true,"Tree inspection camera").Components.Create<CameraComponent>();
				camera.FieldOfView=62; camera.BackgroundColor=new Color(.20f,.25f,.30f);
				var sun=new GameObject(true,"Inspection daylight").Components.Create<DirectionalLight>();
				sun.LightColor=new Color(.9f,.92f,.95f); sun.SkyColor=new Color(.4f,.45f,.5f);
				sun.WorldRotation=Rotation.From(45,30,0);
			}
			using var bitmap=new Bitmap(1000,1000);
			foreach(var variant in new[]{"a","b","c"})
			{
				GameObject tree; Model model;
				using(scene.Push())
				{
					tree=new GameObject(true,"Inspected pine");
					model=Model.Load($"models/maps/forestbase/pine/pine_{variant}.vmdl");
					tree.Components.Create<ModelRenderer>().Model=model;
					report.Add(new { variant, bounds=model.Bounds.ToString(), error=model.IsError });
					camera.WorldPosition=Plan(-450,-1000,420); camera.WorldRotation=Rotation.LookAt(Plan(0,0,420)-camera.WorldPosition);
					scene.EditorTick(1,.016f);
				}
				await Task.Delay(1500);
				using(scene.Push())camera.RenderToBitmap(bitmap);
				File.WriteAllBytes(Path.Combine(Folder,$"pine-{variant}.png"),bitmap.ToPng());
				using(scene.Push())tree.DestroyImmediate();
			}
			File.WriteAllText(Path.Combine(Folder,"tree-qa.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
		}
		catch(Exception e){Log.Warning(e);}
		finally{scene.Destroy();}
	}
	[ConCmd("hc1_forestbase_firqa")]
	public static async void Firs(string kindFilter="all")
	{
		Directory.CreateDirectory(Folder);
		var report=new System.Collections.Generic.List<object>();
		foreach(var kind in new[]{"fir","sapling"})
		foreach(var variant in new[]{"a","b","c"})
		{
		if(kindFilter!="all"&&kindFilter!=kind)continue;
		var scene=new Scene();
		try
		{
			using(scene.Push())scene.Deserialize(JsonNode.Parse("{\"GameObjects\":[],\"SceneProperties\":{\"WantsSystemScene\":false,\"NavMesh\":{\"Enabled\":false}},\"ResourceVersion\":3}").AsObject());
			CameraComponent camera;
			using(scene.Push())
			{
				camera=new GameObject(true,"Fir inspection camera").Components.Create<CameraComponent>();
				camera.FieldOfView=62;camera.BackgroundColor=new Color(.20f,.25f,.30f);camera.ZFar=30000;
				var sun=new GameObject(true,"Inspection daylight").Components.Create<DirectionalLight>();
				sun.LightColor=new Color(.9f,.92f,.95f);sun.SkyColor=new Color(.4f,.45f,.5f);
				sun.WorldRotation=Rotation.From(45,30,0);
			}
			using var bitmap=new Bitmap(1000,1000);
			{
				GameObject tree;Model model;
				using(scene.Push())
				{
					tree=new GameObject(true,"Inspected "+kind);
					model=Model.Load($"models/maps/forestbase/{kind}/{kind}_{variant}.vmdl");
					tree.Components.Create<ModelRenderer>().Model=model;
					report.Add(new{kind,variant,bounds=model.Bounds.ToString(),error=model.IsError});
					var height=model.Bounds.Size.z;
					var center=model.Bounds.Center;
					camera.WorldPosition=center+new Vector3(-height*1.2f,-height*.6f,height*.05f);
					camera.WorldRotation=Rotation.LookAt(center-camera.WorldPosition);
					scene.EditorTick(1,.016f);
				}
				await Task.Delay(1500);
				using(scene.Push())
				{
					scene.EditorTick(.016f,.016f);
					camera.RenderToBitmap(bitmap,false);
					Log.Info($"Fir QA {kind}-{variant}: {scene.GetAllComponents<ModelRenderer>().Count()} renderers, bounds {model.Bounds}");
				}
				File.WriteAllBytes(Path.Combine(Folder,$"{kind}-{variant}.png"),bitmap.ToPng());
				using(scene.Push())
				{
					tree.Enabled=false;
					scene.EditorTick(.016f,.016f);
					tree.DestroyImmediate();
				}
			}
		}
		catch(Exception e){Log.Warning(e);}
		finally{scene.Destroy();}
		}
		File.WriteAllText(Path.Combine(Folder,"fir-qa.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
		Log.Info("Forest Base fir inspection complete");
	}
	[ConCmd( "hc1_forestbase_modelbounds" )]
	public static void ModelBounds()
	{
		var data = SceneEditorSession.Active.Scene.GetAllComponents<ModelRenderer>().Where(x=>x.GameObject.Parent?.Name == "Military Outpost")
			.Select(x=>new { name=x.GameObject.Name, bounds=x.Model.Bounds.ToString(), pos=x.WorldPosition.ToString() }).ToArray();
		File.WriteAllText( Path.Combine(Folder,"model-bounds.json"),JsonSerializer.Serialize(data,new JsonSerializerOptions { WriteIndented=true }) );
	}
	[ConCmd( "hc1_forestbase_save_navsettings" )]
	public static void SaveNavSettings()
	{
		var scene = SceneEditorSession.Active.Scene;
		if ( scene.Name != "forestbase" ) return;
		scene.NavMesh.IsEnabled = true; scene.NavMesh.CustomBounds = true;
		scene.NavMesh.AgentRadius = 24; scene.NavMesh.AgentHeight = 72; scene.NavMesh.AgentStepSize = 18;
		scene.NavMesh.Bounds = new BBox(new Vector3(-1730,-1550,-100),new Vector3(1450,1550,650));
		EditorScene.SaveSession();
	}

	[ConCmd( "hc1_forestbase_navqa" )]
	public static async void Navigation()
	{
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/ForestBase/forestbase.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
				if ( new[] { "Military Outpost", "Closed Player Boundary" }.Contains( item["Name"]?.GetValue<string>() ) ) objects.Add( item.DeepClone() );
			root["GameObjects"] = objects;
			root["SceneProperties"]["WantsSystemScene"] = false;
			using ( scene.Push() )
			{
				scene.Deserialize( root ); scene.EditorTick( .016f, .016f );
				scene.NavMesh.IsEnabled = true;
				scene.NavMesh.IncludeStaticBodies = true;
				scene.NavMesh.IncludeKeyframedBodies = true;
				scene.NavMesh.AgentHeight = 72;
				scene.NavMesh.AgentRadius = 24;
				scene.NavMesh.AgentStepSize = 18;
				scene.NavMesh.CustomBounds = true;
				scene.NavMesh.Bounds = new BBox( new Vector3(-1730,-1550,-100),new Vector3(1450,1550,650) );
				await scene.NavMesh.Generate( scene.PhysicsWorld );
			}
			for ( var i = 0; i < 80; i++ )
			{
				await Task.Delay( 60 );
				using ( scene.Push() ) scene.EditorTick( .06f, .016f );
			}
			var targets = new[] { ("Blue Spawn",Plan(1008,1320,2)),("Motor Pool",Plan(-1000,-760,2)),
				("Barracks Lower",Plan(-1050,770,98)),("Barracks Upper",Plan(-1050,770,242)),
				("Command Lower",Plan(100,850,98)),("Command Upper",Plan(100,850,242)),
				("Command Roof",Plan(250,840,386)),("Workshop",Plan(1110,320,2)),
				("West Bridge",Plan(-330,880,242)),("East Bridge",Plan(840,920,242)),
				("Logistics",Plan(-40,-90,2)),("Storage",Plan(1120,-390,2)),
				("Barracks West Lower Room",Plan(-1100,980,98)),("Barracks West Upper Room",Plan(-1100,980,242)),
				("Barracks East Lower Room",Plan(-850,990,98)),("Barracks East Upper Room",Plan(-850,990,242)),
				("Command West Lower Room",Plan(95,1010,98)),("Command West Upper Room",Plan(95,1010,242)),
				("Command East Lower Room",Plan(350,1010,98)),("Command East Upper Room",Plan(350,1010,242)),
				("Roof West Approach",Plan(-30,1183,242)),("Roof West Stair Midpoint",Plan(120,1183,322)),
				("Roof Stair Landing",Plan(265,1183,386)),("Roof Rear Deck",Plan(265,1100,386)) };
			GameObject walker;
			Facepunch.CharacterController controller;
			using ( scene.Push() )
			{
				walker = new GameObject( true, "QA character controller" );
				controller = walker.Components.Create<Facepunch.CharacterController>();
				controller.Radius = 16; controller.Height = 64; controller.StepHeight = 18;
				controller.UseCollisionRules = false;
			}
			var results = targets.Select( t => {
				var calculated=scene.NavMesh.CalculatePath(new Sandbox.Navigation.CalculatePathRequest {
					Start=Plan(-1420,-1280,2),Target=t.Item2 });
				var path=calculated.Points?.Select(p=>p.Position).ToList();
				walker.WorldPosition = Plan(-1420,-1280,2);
				var obstruction = "";
				var hitName = "";
				using ( scene.Push() )
					foreach ( var next in path ?? new System.Collections.Generic.List<Vector3>() )
					{
						var begin = walker.WorldPosition;
						var steps = Math.Max( 1, (int)Math.Ceiling( (next-begin).Length / 6f ) );
						for ( var step = 1; step <= steps; step++ )
						{
							var desired = Vector3.Lerp( begin, next, step/(float)steps );
							controller.MoveTo( desired, true );
						// A capsule stands on a tread ahead of the navmesh's smoothed stair slope.
						// Compare plan progress; positive height differences are normal on steps.
						if ( (walker.WorldPosition-desired).WithZ(0).Length > 28f || walker.WorldPosition.z < desired.z-30f )
						{
							obstruction = walker.WorldPosition.ToString();
							var hit = scene.Trace.Box( new BBox(new Vector3(-16,-16,18),new Vector3(16,16,64)),walker.WorldPosition,desired ).Run();
							hitName = hit.GameObject?.Name ?? ""; break;
						}
						}
						if ( obstruction.Length > 0 ) break;
					}
				var endpoint=path?.LastOrDefault() ?? Vector3.Zero;
				var endpointError=(endpoint-t.Item2).WithZ(0).Length;
				var reachedTarget=calculated.Status==Sandbox.Navigation.NavMeshPathStatus.Complete && path?.Count>1
					&& endpointError<=24f && MathF.Abs(endpoint.z-t.Item2.z)<=30f;
				return new { name = t.Item1, target=t.Item2.ToString(),endpoint=endpoint.ToString(),endpointError,
					pathStatus=calculated.Status.ToString(),
					reachable = reachedTarget, controllerClear = obstruction.Length == 0 && reachedTarget, obstruction, hitName, points = path?.Select( p => p.ToString() ).ToArray() };
			} ).ToArray();
			var stairChecks = new System.Collections.Generic.List<object>();
			using ( scene.Push() )
				foreach ( var route in JsonNode.Parse(File.ReadAllText(Path.Combine(Folder,"layout.json")))["routes"].AsArray() )
				{
					if ( route["kind"].GetValue<string>() != "stairs" ) continue;
					Vector3 Point(JsonNode p) => Plan(p[0].GetValue<float>(),p[1].GetValue<float>(),p[2].GetValue<float>()) + Vector3.Up*2;
					var a=Point(route["start"]); var b=Point(route["end"]);
					a -= (b-a).WithZ(0).Normal*32; // approach the first riser from clear floor
					foreach ( var reverse in new[] { false,true } )
					{
						var begin=reverse?b:a; var end=reverse?a:b; walker.WorldPosition=begin;
						var count=(int)Math.Ceiling((end-begin).Length/5f); var clear=true;
						for(var i=1;i<=count;i++)
						{
							var desired=Vector3.Lerp(begin,end,i/(float)count); controller.MoveTo(desired,true);
							if((walker.WorldPosition-desired).WithZ(0).Length>28f || walker.WorldPosition.z<desired.z-30f) { clear=false; break; }
						}
						stairChecks.Add(new { start=begin.ToString(),end=end.ToString(),reverse,clear,position=walker.WorldPosition.ToString() });
					}
				}
			File.WriteAllText( Path.Combine( Folder, "engine-nav.json" ), JsonSerializer.Serialize( new { generating = scene.NavMesh.IsGenerating, bounds = scene.NavMesh.Bounds.ToString(), statics = scene.NavMesh.IncludeStaticBodies, results,stairChecks },new JsonSerializerOptions { WriteIndented = true } ) );
		}
		catch ( Exception e ) { File.WriteAllText( Path.Combine( Folder,"nav-error.txt" ),e.ToString() ); }
		finally { scene.Destroy(); }
	}

	[ConCmd( "hc1_forestbase_cascade_diagnostic" )]
	public static async void CascadeDiagnostic()
	{
		var scene=new Scene();
		try
		{
			var root=JsonNode.Parse(File.ReadAllText(Path.Combine(Project.Current.GetRootPath(),"Assets/scenes/maps/ForestBase/forestbase.scene"))).AsObject();
			var objects=new JsonArray();
			foreach(var item in root["GameObjects"].AsArray())
				if(new[]{"Military Outpost","Forest Backdrop","Cool Daylight","Sky","Forest Mist","Rain Reflections"}.Contains(item["Name"]?.GetValue<string>()))objects.Add(item.DeepClone());
			root["GameObjects"]=objects;root["SceneProperties"]["NavMesh"]["Enabled"]=false;root["SceneProperties"]["WantsSystemScene"]=false;
			using(scene.Push())scene.Deserialize(root);
			CameraComponent camera;
			using(scene.Push())
			{
				camera=new GameObject(true,"Cascade diagnostic camera").Components.Create<CameraComponent>();
				camera.FieldOfView=72;camera.ZFar=18000;camera.EnablePostProcessing=true;
				camera.WorldPosition=Plan(450,1800,520);camera.WorldRotation=Rotation.LookAt(Plan(410,3450,830)-camera.WorldPosition);
			}
			using var bitmap=new Bitmap(1600,900);
			for(int variant=0;variant<3;variant++)
			{
				if(variant==1)foreach(var go in scene.GetAllObjects(true).Where(x=>x.Name.StartsWith("Cascade cliff")))go.Enabled=false;
				if(variant==2)
				{
					foreach(var go in scene.GetAllObjects(true).Where(x=>x.Name.StartsWith("Cascade cliff")))go.Enabled=true;
					foreach(var light in scene.GetAllComponents<DirectionalLight>())light.Shadows=false;
				}
				using(scene.Push())scene.EditorTick(1,.016f);
				await Task.Delay(700);
				using(scene.Push()){scene.EditorTick(1,.016f);camera.RenderToBitmap(bitmap);}
				await Task.Delay(200);
				using(scene.Push())camera.RenderToBitmap(bitmap);
				File.WriteAllBytes(Path.Combine(Folder,$"cascade-diagnostic-{variant}.png"),bitmap.ToPng());
			}
		}
		catch(Exception e){Log.Error(e);}
		finally{scene.Destroy();}
	}

	[ConCmd( "hc1_forestbase_materials" )]
	public static void Materials()
	{
		var model=Model.Load("models/maps/forestbase/vista.vmdl");
		var report=model.Materials.Select(m=>new {
			material=m.ToString(), shader=m.ShaderName,
			color=m.GetTexture("Color")?.ToString(), rawColor=m.GetTexture("g_tColor")?.ToString()
		}).ToArray();
		Directory.CreateDirectory(Folder);
		File.WriteAllText(Path.Combine(Folder,"vista-materials.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
	}
	[ConCmd( "hc1_forestbase_qa" )]
	public static async void Run(string viewFilter="all")
	{
		if ( running ) return;
		running = true;
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/ForestBase/forestbase.scene" ) ) ).AsObject();
			var original = root["GameObjects"].AsArray();
			var objects = new JsonArray();
			foreach ( var item in original )
				if ( new[] { "Military Outpost", "Forest Backdrop", "Cool Daylight", "Sky", "Forest Mist", "Warm Military Lights", "Reflections", "Rain Reflections", "Closed Player Boundary" }.Contains( item["Name"]?.GetValue<string>() ) ) objects.Add( item.DeepClone() );
			root["GameObjects"] = objects;
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				camera = new GameObject( true, "Forest Base QA Camera" ).Components.Create<CameraComponent>();
				camera.FieldOfView = 72; camera.ZNear = 1; camera.ZFar = 18000; camera.EnablePostProcessing=true;
				// Match the existing player's contact shading in inspection views.
				var ao=camera.GameObject.Components.Create<AmbientOcclusion>();
				ao.Intensity=.15f; ao.Radius=128; ao.FalloffRange=.75f;
				scene.EditorTick( .016f, .016f );
			}
			await Task.Delay( 1500 );
			var errors = scene.GetAllComponents<ModelRenderer>().Where( x => x.Model == null || x.Model.IsError ).Select( x => x.GameObject.Name ).ToArray();
			var views = new[] {
				("aerial", Plan(-2600,-2900,2000), Plan(0,200,90)),
				("entrance", Plan(0,-1680,68), Plan(50,900,260)),
				("drain-detail", Plan(-130,-1320,22), Plan(-230,-1310,0)),
				("motor", Plan(-720,-775,68), Plan(-1100,-480,100)),
				("apc-detail", Plan(-690,-1200,84), Plan(-900,-995,85)),
				("vehicle-front", Plan(-1160,-980,76), Plan(-1260,-870,85)),
				("logistics", Plan(750,-1200,68), Plan(450,150,80)),
				("cargo-detail", Plan(800,-530,92), Plan(680,-720,65)),
				("command", Plan(-190,560,164), Plan(250,900,230)),
				("barracks", Plan(-1100,985,164), Plan(-1210,1020,140)),
				("barracks-upper", Plan(-1100,985,308), Plan(-1210,1020,284)),
				("control", Plan(355,985,308), Plan(285,1080,286)),
				("roof-detail", Plan(520,810,492), Plan(355,925,428)),
				("workshop", Plan(1335,370,68), Plan(1260,750,80)),
				("catwalk", Plan(-395,873,308), Plan(265,920,310)),
				("waterfall", Plan(450,1800,520), Plan(410,3450,830)),
				("waterfall-foot", Plan(430,2500,450), Plan(425,3500,-200)),
				("gorge", Plan(-480,-2390,230), Plan(0,-1730,-155)) };
			if(!string.Equals(viewFilter,"all",StringComparison.OrdinalIgnoreCase))
			{
				var requested=viewFilter.Split(',').Select(x=>x.Trim()).ToArray();
				views=views.Where(x=>requested.Contains(x.Item1)).ToArray();
				if(views.Length==0)throw new ArgumentException("No matching Forest Base QA views.");
			}
			using var bitmap = new Bitmap( 1600, 900 );
			foreach ( var (name, eye, target) in views )
			{
				using ( scene.Push() )
				{
					camera.WorldPosition = eye; camera.WorldRotation = Rotation.LookAt( target-eye );
					scene.EditorTick( 1f, .016f ); camera.RenderToBitmap( bitmap );
				}
				await Task.Delay( 200 );
				using ( scene.Push() ) camera.RenderToBitmap( bitmap );
				File.WriteAllBytes( Path.Combine( Folder, name+".png" ), bitmap.ToPng() );
			}
			var spawns = JsonNode.Parse( File.ReadAllText( Path.Combine( Folder, "layout.json" ) ) );
			var results = new System.Collections.Generic.List<object>();
			var exposure = new System.Collections.Generic.List<object>();
			using ( scene.Push() )
			{
				foreach ( var kind in new[] { "red", "blue", "dm" } )
					foreach ( var point in spawns[kind].AsArray() )
					{
						var p = Plan( point[0].GetValue<float>(), point[1].GetValue<float>(), point[2].GetValue<float>() );
						var floor = scene.Trace.Ray( p + Vector3.Up * 8, p - Vector3.Up * 24 ).Run();
						var space = scene.Trace.Sphere( 16, p + Vector3.Up * 18, p + Vector3.Up * 56 ).Run();
						results.Add( new { kind, position = p.ToString(), floor = floor.Hit, floorZ = floor.EndPosition.z, blocked = space.Hit || space.StartedSolid, objectName = space.GameObject?.Name } );
					}
				foreach ( var (a,b) in new[] { (Plan(0,-1200,68),Plan(0,-2000,68)), (Plan(-1400,0,68),Plan(-2000,0,68)),
					(Plan(1400,0,68),Plan(2000,0,68)), (Plan(0,1300,68),Plan(0,1800,68)),
					(Plan(0,1300,900),Plan(0,1800,900)), (Plan(0,0,900),Plan(0,0,1900)) } )
				{
					var hit = scene.Trace.Sphere( 16,a,b ).Run();
					results.Add( new { kind = "boundary", position = a.ToString(), blocked = hit.Hit, objectName = hit.GameObject?.Name } );
				}
				Vector3 TruckPoint(float x,float y,float z)
				{
					var yaw=-20f*MathF.PI/180;
					return Plan(-1360+x*MathF.Cos(yaw)-y*MathF.Sin(yaw),-840+x*MathF.Sin(yaw)+y*MathF.Cos(yaw),z);
				}
				foreach(var (name,a,b,expected) in new[] {
					("APC front tire",Plan(-794,-1105,23),Plan(-794,-1035,23),true),
					("APC underbody wheel gap",Plan(-828,-1105,23),Plan(-828,-1035,23),false),
					("Transport front tire",TruckPoint(93,-100,22),TruckPoint(93,-35,22),true),
					("Transport underbody wheel gap",TruckPoint(20,-100,22),TruckPoint(20,-35,22),false) })
				{
					var hit=scene.Trace.Ray(a,b).Run();
					results.Add(new { kind="vehicle-collision",name,expected,blocked=hit.Hit,passed=hit.Hit==expected,objectName=hit.GameObject?.Name });
				}
				// Sample standing sightlines from the accessible command roof and both bridges.
				foreach ( var (name,eye) in new[] { ("Roof SW",Plan(-20,725,448)), ("Roof SE",Plan(550,725,448)),
					("Roof NW",Plan(-20,1100,448)), ("Roof NE",Plan(550,1100,448)),
					("Roof Center",Plan(265,920,448)), ("West Bridge",Plan(-330,880,304)), ("East Bridge",Plan(840,920,304)) } )
					foreach ( var kind in new[] { "red", "blue" } )
					{
						var visible = new System.Collections.Generic.List<int>(); var index=0;
						foreach ( var point in spawns[kind].AsArray() )
						{
							var target = Plan(point[0].GetValue<float>(),point[1].GetValue<float>(),point[2].GetValue<float>()+56);
							if ( !scene.Trace.Ray(eye,target).Run().Hit ) visible.Add(index);
							index++;
						}
						exposure.Add(new { vantage=name, team=kind, visible=visible.ToArray(), total=index });
					}
			}
			var lighting=new {
				cameraPostProcessing=camera.EnablePostProcessing,
				volumetricFog=scene.GetAllComponents<VolumetricFogVolume>().Select(x=>new{name=x.GameObject.Name,x.Strength,x.Color,x.FalloffExponent,x.Bounds,position=x.WorldPosition.ToString()}).ToArray(),
				sun=scene.GetAllComponents<DirectionalLight>().Select(x=>new{x.LightColor,x.SkyColor}).ToArray(),
					fog=scene.GetAllComponents<GradientFog>().Select(x=>new{x.Color,x.Height,x.StartDistance,x.EndDistance}).ToArray(),
				sky=scene.GetAllComponents<SkyBox2D>().Select(x=>new{x.Tint,x.SkyIndirectLighting}).ToArray(),
				tone=scene.GetAllComponents<Tonemapping>().Select(x=>new{x.Mode,x.ExposureMethod,x.MinimumExposure,x.MaximumExposure,x.ExposureCompensation}).ToArray(),
				volumes=scene.GetAllComponents<PostProcessVolume>().Select(x=>new{x.IsInfinite,x.BlendWeight,x.Priority}).ToArray(),
				cliffs=scene.GetAllComponents<ModelRenderer>().Where(x=>x.GameObject.Name.StartsWith("Cascade cliff")).Select(x=>new{name=x.GameObject.Name,bounds=x.Model.Bounds.ToString(),position=x.WorldPosition.ToString(),scale=x.WorldScale.ToString()}).ToArray(),
				pointCount=scene.GetAllComponents<PointLight>().Count(),
				spots=scene.GetAllComponents<SpotLight>().Select(x=>new {
					name=x.GameObject.Name,x.ConeInner,x.ConeOuter,x.Shadows,x.Radius,x.LightColor,x.FogMode,x.FogStrength,
					direction=x.WorldRotation.Forward.ToString() }).ToArray()
			};
			File.WriteAllText( Path.Combine( Folder, "engine-qa.json" ), JsonSerializer.Serialize( new { capturedViews=views.Select(x=>x.Item1).ToArray(), errors, results, exposure, lighting }, new JsonSerializerOptions { WriteIndented = true } ) );
			if(views.Any(x=>x.Item1=="aerial"))
				File.WriteAllBytes( Path.Combine( Project.Current.GetAssetsPath(), "ui/maps/forestbase.png" ), File.ReadAllBytes( Path.Combine( Folder, "aerial.png" ) ) );
			Log.Info( $"Forest Base QA complete: {Folder}" );
		}
		catch ( Exception e )
		{
			File.WriteAllText( Path.Combine( Folder, "qa-error.txt" ), e.ToString() );
			Log.Warning( $"Forest Base QA failed: {e}" );
		}
		finally { scene.Destroy(); running = false; }
	}
}
