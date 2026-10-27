Vector3 Plan(float e,float n,float z)=>new(n,-e,z);var Folder="C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/stair-landings-stage-20261021";var scene = new Scene();
		try
		{
			var root = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/ForestBase/forestbase.scene" ) ) ).AsObject();
			var objects = new System.Text.Json.Nodes.JsonArray();
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
				("Roof Stair Landing",Plan(265,1183,386)),("Roof Rear Deck",Plan(265,1100,386)),("Barracks East Upper Door",Plan(-634,850,242)),("Command East Upper Door",Plan(551,920,242)) };
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
				foreach ( var route in System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText("C:/Users/mimi-/Documents/S&box Projects/hc1/output/forestbase/stair-landings-stage-20261021/layout.json"))["routes"].AsArray() )
				{
					if ( route["kind"].GetValue<string>() != "stairs" ) continue;
					Vector3 Point(System.Text.Json.Nodes.JsonNode p) => Plan(p[0].GetValue<float>(),p[1].GetValue<float>(),p[2].GetValue<float>()) + Vector3.Up*2;
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
			return new { generating = scene.NavMesh.IsGenerating, bounds = scene.NavMesh.Bounds.ToString(), statics = scene.NavMesh.IncludeStaticBodies, results,stairChecks };
		}
		catch ( Exception e ) { throw new Exception("Native navigation check failed",e); }
		finally { scene.Destroy(); }