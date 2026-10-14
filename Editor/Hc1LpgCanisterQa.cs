using Sandbox;
using Editor;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Text.Json.Nodes;
using System.Threading.Tasks;

/// <summary>Checks the LPG assets, hit volumes and damage route in a temporary scene, preserving the open match.</summary>
public static class Hc1LpgCanisterQa
{
	static bool _running;
	static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/lowtide/lpg" );

	[ConCmd( "hc1_lpg_canister_qa" )]
	public static async void Run( bool forceCompile = false )
	{
		if ( _running ) return;
		_running = true;
		Directory.CreateDirectory( Folder );
		File.WriteAllText( Path.Combine( Folder, "status.txt" ), "RUNNING" );
		var report = new StringBuilder();
		var scene = new Scene();
		try
		{
			foreach ( var resource in new[] { "models/props/lowtide/lpg_canister.vmdl", "models/props/lowtide/lpg_canister_ruptured.vmdl",
				"models/props/lowtide/lpg_canister_cap.vmdl", "models/maps/lowtide/lowtide_dress_east.vmdl", "models/maps/lowtide/lowtide_dress_west.vmdl",
				"sounds/world/lpg/leak.sound", "sounds/world/lpg/jet.sound" } )
				Report( AssetSystem.FindByPath( resource )?.Compile( forceCompile ) == true, $"Compiled {resource}", report );
			await Task.Delay( 1500 );
			var root = JsonNode.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), "Assets/scenes/maps/Lowtide/lowtide.scene" ) ) ).AsObject();
			var objects = new JsonArray();
			foreach ( var item in root["GameObjects"].AsArray() )
			{
				var name = item["Name"]?.GetValue<string>();
				if ( name is not null && (name is "Sun" or "Sky" or "Look" or "Lowtide" || name.StartsWith( "Forklift LPG" )) )
					objects.Add( item.DeepClone() );
			}
			root["GameObjects"] = objects;
			// The temporary copies must never share RPC ids with the user's live map.
			FreshIds( root );
			root["SceneProperties"]["NavMesh"]["Enabled"] = false;
			root["SceneProperties"]["WantsSystemScene"] = false;
			CameraComponent camera;
			LpgCanister bottle;
			using ( scene.Push() )
			{
				scene.Deserialize( root );
				var bottles = scene.GetAllComponents<LpgCanister>().ToArray();
				Report( bottles.Length == 4, "Four independent map cylinders", report );
				foreach ( var candidate in bottles )
				{
					Report( candidate.GameObject.Root == candidate.GameObject, "Cylinder is an independent root for blast cover", report );
					Report( candidate.IntactModel is not null && !candidate.IntactModel.IsError, "Intact model loads", report );
					Report( candidate.RupturedModel is not null && !candidate.RupturedModel.IsError, "Ruptured model loads", report );
					Report( candidate.IntactModel.Materials.All( m => m is not null && !m.IsError ), "Tank materials load", report );
				}
				bottle = bottles.First( b => b.GameObject.Name.Contains( "east warehouse" ) );
				var eye = bottle.WorldPosition + new Vector3( -85f, -140f, 45f );
				var holder = new GameObject( false, "LPG QA camera" );
				camera = holder.AddComponent<CameraComponent>();
				camera.WorldPosition = eye;
				camera.WorldRotation = Rotation.LookAt( bottle.WorldPosition - eye );
				camera.FieldOfView = 42f;
				camera.ZNear = 0.2f;
				camera.EnablePostProcessing = true;
				var tone = holder.AddComponent<Tonemapping>();
				tone.Mode = Tonemapping.TonemappingMode.ACES;
				tone.AutoExposureEnabled = false;
				tone.ExposureCompensation = 1f;
				holder.Enabled = true;
				var hit = scene.Trace.Ray( eye, bottle.WorldPosition ).Run();
				Report( hit.GameObject == bottle.GameObject, "Shot at the cylinder reaches its own collider", report );
				var nearMiss = scene.Trace.Ray( bottle.WorldPosition + Vector3.Left * 70f + Vector3.Up * 10f,
					bottle.WorldPosition + Vector3.Right * 70f + Vector3.Up * 10f ).Run();
				Report( nearMiss.GameObject != bottle.GameObject, "Shot above the cylinder misses its hit volume", report );
				Report( bottle.GameObject.TakeDamage( new Facepunch.DamageInfo( null, 20f, Position: hit.EndPosition,
					Force: hit.Direction * 20f ) ) && bottle.Phase == LpgCanisterPhase.Leaking, "Weapon damage route punctures the cylinder", report );
				bottle.TakeDamage( new Facepunch.DamageInfo( null, 20f, Flags: DamageFlags.Melee ) );
				Report( bottle.Holes == 1, "Knife damage cannot puncture the pressure vessel", report );
				var wall = new GameObject( true, "LPG QA heat shield" );
				wall.WorldPosition = new Vector3( 50f, 0f, 1000f );
				wall.AddComponent<BoxCollider>().Scale = new Vector3( 12f, 100f, 100f );
				var visible = typeof( LpgCanister ).GetMethod( "Visible", BindingFlags.Instance | BindingFlags.NonPublic );
				Report( !(bool)visible.Invoke( bottle, new object[] { new Vector3( 0f, 0f, 1000f ), new Vector3( 100f, 0f, 1000f ) } ),
					"Solid cover blocks heat and flame exposure", report );
				wall.Destroy();
			}
			await Capture( scene, camera, bottle, "leaking" );
			using ( scene.Push() )
			{
				bottle.OnDamage( new Sandbox.DamageInfo( 1f, null, null ) { Tags = new TagSet( new[] { "burn" } ) } );
				Report( bottle.Phase == LpgCanisterPhase.Burning, "A fire source ignites released gas", report );
			}
			await Capture( scene, camera, bottle, "burning" );
			using ( scene.Push() )
			{
				var state = (LpgCanisterState)typeof( LpgCanister ).GetField( "_state", BindingFlags.Instance | BindingFlags.NonPublic ).GetValue( bottle );
				for ( int i = 0; i < 700; i++ ) state.Step( 0.1f, 0f, false );
				Report( bottle.Phase == LpgCanisterPhase.Ruptured, "Sustained flame produces a single pressure rupture", report );
				Invoke( bottle, "Publish", true );
				Report( !bottle.GetComponent<ModelCollider>( true ).Enabled, "Rupture disables the pressure vessel collider", report );
				Report( bottle.GetComponent<ModelRenderer>().Model == bottle.RupturedModel, "Rupture shows the torn shell", report );
			}
			await Capture( scene, camera, bottle, "ruptured" );
			using ( scene.Push() )
			{
				((Sandbox.Events.IGameEventHandler<BetweenRoundCleanupEvent>)bottle).OnGameEvent( new BetweenRoundCleanupEvent() );
				Report( bottle.Phase == LpgCanisterPhase.Intact && bottle.Fuel == 1f && bottle.GetComponent<ModelCollider>( true ).Enabled,
					"Round cleanup restores the cylinder and hit volume", report );
				Report( !bottle.GetComponentsInChildren<LpgCanisterFragment>().Any( f => f.Active ), "Round cleanup removes local fragments", report );
			}
			File.WriteAllText( Path.Combine( Folder, "status.txt" ), "PASS\n" + report );
			Log.Info( "HC1_LPG_CANISTER_QA PASS" );
		}
		catch ( Exception e )
		{
			File.WriteAllText( Path.Combine( Folder, "status.txt" ), "FAIL\n" + report + "\n" + e );
			Log.Warning( e );
		}
		finally { scene.Destroy(); _running = false; }
	}

	static async Task Capture( Scene scene, CameraComponent camera, LpgCanister bottle, string name )
	{
		using var bitmap = new Bitmap( 1280, 720 );
		for ( int i = 0; i < 25; i++ )
		{
			using ( scene.Push() )
			{
				scene.EditorTick( (i + 1) * 0.016f, 0.016f );
				Invoke( bottle, "UpdateVisuals", 0.016f );
				camera.RenderToBitmap( bitmap );
			}
			await Task.Delay( 20 );
		}
		File.WriteAllBytes( Path.Combine( Folder, name + ".png" ), bitmap.ToPng() );
	}

	static void Invoke( object target, string name, params object[] args ) =>
		target.GetType().GetMethod( name, BindingFlags.Instance | BindingFlags.NonPublic ).Invoke( target, args );

	static void Report( bool pass, string name, StringBuilder report )
	{
		report.AppendLine( $"{(pass ? "PASS" : "FAIL")}: {name}" );
		File.WriteAllText( Path.Combine( Folder, "status.txt" ), "RUNNING\n" + report );
		if ( !pass ) throw new Exception( name );
	}

	static void FreshIds( JsonNode node )
	{
		if ( node is JsonObject obj )
		{
			if ( obj.ContainsKey( "__guid" ) ) obj["__guid"] = JsonValue.Create( Guid.NewGuid() );
			foreach ( var pair in obj.ToArray() ) FreshIds( pair.Value );
		}
		else if ( node is JsonArray array ) foreach ( var child in array ) FreshIds( child );
	}
}
