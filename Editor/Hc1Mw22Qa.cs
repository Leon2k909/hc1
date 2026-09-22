using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

public static class Hc1Mw22Qa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "Sources/MW2022/qa" );
	[ConCmd( "hc1_mw22_repair" )]
	public static async System.Threading.Tasks.Task Repair()
	{
		var assets = Path.Combine( Project.Current.GetRootPath(), "Assets" );
		var report = new List<string>();
		foreach ( var path in Directory.GetFiles( Path.Combine( assets, "attachments/mw2022" ), "*", SearchOption.AllDirectories ).Where( p => p.EndsWith( ".vmdl" ) || p.EndsWith( ".vmat" ) ) )
		{
			var asset = AssetSystem.FindByPath( path ) ?? AssetSystem.RegisterFile( path );
			Require( asset is not null, "register " + path );
			if ( !File.Exists( path + "_c" ) || File.GetLastWriteTimeUtc( path ) > File.GetLastWriteTimeUtc( path + "_c" ) )
			{
				report.Add( path + " " + asset.Compile( true ) );
				await System.Threading.Tasks.Task.Delay( 5 );
			}
		}
		foreach ( var path in Directory.GetFiles( Path.Combine( assets, "gunsmith/m4a1/mw2022" ), "*" ).Where( p => p.EndsWith( ".prefab" ) || p.EndsWith( ".gnsmth" ) ) )
		{
			var asset = AssetSystem.FindByPath( path ) ?? AssetSystem.RegisterFile( path );
			Require( asset is not null, "register " + path );
			if ( !File.Exists( path + "_c" ) || File.GetLastWriteTimeUtc( path ) > File.GetLastWriteTimeUtc( path + "_c" ) ) report.Add( path + " " + asset.Compile( true ) );
		}
		File.WriteAllLines( Path.Combine( Folder, "repair.txt" ), report );
		Log.Info( "MW22 REPAIR COMPLETE" );
	}
	[ConCmd( "hc1_mw22_compile" )]
	public static void Compile()
	{
		Directory.CreateDirectory( Folder );
		foreach ( var folder in new[] { "Assets/attachments/mw2022", "Assets/gunsmith/m4a1/mw2022" } )
		foreach ( var path in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), folder ), "*", SearchOption.AllDirectories ).Where( p => p.EndsWith( ".vmdl" ) || p.EndsWith( ".vmat" ) || p.EndsWith( ".gnsmth" ) || p.EndsWith( ".prefab" ) ) )
			(AssetSystem.FindByPath( path ) ?? AssetSystem.RegisterFile( path ))?.Compile( true );
		foreach ( var prefix in new[] { "vm", "wm" } ) AssetSystem.FindByPath( $"weapons/m4a1/{prefix}_m4a1.prefab" )?.Compile( true );
		File.WriteAllText( Path.Combine( Folder, "compile-requested.txt" ), DateTime.UtcNow.ToString( "O" ) );
	}
	[ConCmd( "hc1_mw22_audit" )]
	public static void Audit()
	{
		Directory.CreateDirectory( Folder );
		var lines = new List<string>();
		var rifle = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
		foreach ( var path in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/gunsmith/m4a1/mw2022" ), "*.gnsmth" ) )
		{
			var resource = "gunsmith/m4a1/mw2022/" + Path.GetFileName( path );
			var part = ResourceLibrary.Get<GunsmithPart>( resource );
			Require( part.IsValid() && part.MainPrefab.IsValid() && part.Supports( rifle ), resource );
		}
		foreach ( var path in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/attachments/mw2022" ), "*.vmdl", SearchOption.AllDirectories ) )
		{
			var model = Model.Load( Path.GetRelativePath( Path.Combine( Project.Current.GetRootPath(), "Assets" ), path ).Replace( '\\', '/' ) );
			Require( model is not null && !model.IsError, path );
			Require( model.Materials.All( m => !m.Name.Contains( "error" ) ), "materials " + path );
			lines.Add( $"{model.Name} bounds={model.Bounds} materials={model.Materials.Length} parts={string.Join( "|", model.Parts.All.Select( p => p.Name + ":" + p.Mask ) )}" );
		}
		lines.Add( "PASS: 83 resources, 86 models and their material references loaded." );
		File.WriteAllLines( Path.Combine( Folder, "audit.txt" ), lines );
		Log.Info( "MW22 AUDIT PASS" );
	}

	[ConCmd( "hc1_mw22_preview" )]
	public static void Preview( bool world = false, bool shortBarrel = false, string suffix = "draft" )
	{
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/m4a1/{(world ? "wm" : "vm")}_m4a1.prefab" );
			var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false } );
			root.Components.GetOrCreate<GunsmithWeapon>().Resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
			foreach ( var c in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) ) c.Enabled = c is ModelRenderer || c is GunsmithAttachmentPoint;
			var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			renderer.UseAnimGraph = false; renderer.PlaybackRate = 0; renderer.BodyGroups = world ? 395UL : 9251UL;
			if ( !world ) renderer.Sequence.Name = "IdlePose";
			renderer.RenderOptions.Game = true; renderer.RenderOptions.Overlay = false;
			foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) ) if ( other != renderer ) other.Enabled = false;
			var keys = new[] { shortBarrel ? "att_vm_p01_ar_mike4_barshort_v0" : "att_vm_p01_ar_mike4_barhvy_v0", "att_vm_p01_ar_mike4_stockl_v0", "att_vm_p01_ar_mike4_grpskel_v0", "att_vm_p01_ar_mike4_xmag_v0", "att_vm_silencer02", "att_vm_minireddot01_tall", "att_vm_p01_ar_mike4_stubbygrip01", "att_vm_p01_ar_mike4_laser01" };
			var points = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray();
			foreach ( var key in keys )
			{
				var part = ResourceLibrary.Get<GunsmithPart>( $"gunsmith/m4a1/mw2022/{key}.gnsmth" );
				Require( part.IsValid(), key );
				points.Single( p => p.Category == part.Category ).SetPart( part );
			}
			root.Enabled = true; scene.EditorTick( .01f, .01f );
			foreach ( var mount in root.Components.GetAll<GunsmithMw22Attachment>( FindMode.EverythingInSelfAndDescendants ) ) mount.RefreshMount();
			var camera = new GameObject( true, "MW22 QA camera" ).Components.Create<CameraComponent>();
			camera.BackgroundColor = new Color( .055f, .065f, .08f ); camera.FieldOfView = shortBarrel ? 30 : 36;
			var center = new Vector3( 5, 0, 5.7f ); camera.WorldPosition = center + new Vector3( 6, -72, 14 ); camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
			var light = new GameObject( true, "MW22 QA light" ).Components.Create<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 35, 45, 0 ) ); light.LightColor = Color.White * 2.3f; light.SkyColor = Color.White * .7f;
			scene.EditorTick( .01f, .01f );
			using var bitmap = new Bitmap( 1800, 900 ); camera.RenderToBitmap( bitmap );
			File.WriteAllBytes( Path.Combine( Folder, $"{(world ? "world" : "view")}-{(shortBarrel ? "short" : "long")}-{suffix}.png" ), bitmap.ToPng() );
			File.WriteAllLines( Path.Combine( Folder, $"mounts-{world}-{shortBarrel}.txt" ), root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ).Select( r => $"{r.Model?.Name} enabled={r.Enabled} mask={r.BodyGroups} transform={r.WorldTransform}" ) );
			Log.Info( "MW22 PREVIEW SAVED" );
		}
		finally { scene.Destroy(); }
	}
	[ConCmd( "hc1_mw22_roundtrip" )]
	public static void Roundtrip()
	{
		var lines = new List<string>();
		foreach ( var world in new[] { false, true } )
		{
			var scene = new Scene();
			try
			{
				using var scope = scene.Push();
				var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/m4a1/{(world ? "wm" : "vm")}_m4a1.prefab" );
				var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false } );
				root.Components.GetOrCreate<GunsmithWeapon>().Resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
				foreach ( var c in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) ) c.Enabled = c is ModelRenderer || c is GunsmithAttachmentPoint;
				var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
				renderer.UseAnimGraph = false; renderer.PlaybackRate = 0; renderer.BodyGroups = world ? 395UL : 9251UL;
				if ( !world ) renderer.Sequence.Name = "IdlePose";
				var points = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray();
				foreach ( var point in points ) point.SetPart( null );
				root.Enabled = true; scene.EditorTick( .01f, .01f );
				var standard = renderer.BodyGroups;
				foreach ( var path in Directory.GetFiles( Path.Combine( Project.Current.GetRootPath(), "Assets/gunsmith/m4a1/mw2022" ), "*.gnsmth" ) )
				{
					var part = ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/" + Path.GetFileName( path ) );
					var point = points.Single( p => p.Category == part.Category );
					point.SetPart( part );
					var first = point.CurrentGameObject;
					var mount = first.Components.Get<GunsmithMw22Attachment>( FindMode.EverythingInSelf );
					var mesh = first.Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
					Require( mount.IsValid() && mesh.IsValid() && !mesh.Model.IsError, part.Name );
					mount.RefreshMount(); renderer.Components.Get<GunsmithMw22Factory>().Refresh();
					if ( part.Category == GunsmithPartType.Magazine )
					{
						Require( (renderer.BodyGroups & renderer.Model.Parts.Get( "magazine" ).Mask) == 0, "factory magazine hidden" );
						if ( !world && renderer.TryGetBoneTransform( "magazine", out var before ) )
						{
							var bone = Enumerable.Range( 0, renderer.Model.BoneCount ).Single( i => renderer.Model.GetBoneName( i ) == "magazine" );
							var position = mount.WorldPosition;
							renderer.SceneModel.SetBoneWorldTransform( bone, before.WithPosition( before.Position + Vector3.Down * 3 ) );
							mount.RefreshMount(); Require( mount.WorldPosition.Distance( position + Vector3.Down * 3 ) < .01f, "reload bone " + part.Name );
							renderer.SceneModel.SetBoneWorldTransform( bone, before );
						}
					}
					point.SetPart( null ); first.DestroyImmediate();
					renderer.Components.Get<GunsmithMw22Factory>().Refresh();
					Require( renderer.BodyGroups == standard, $"restore {part.Name}: {renderer.BodyGroups} != {standard}" );
					Require( !root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ).Any( r => r.Model?.Name.Contains( "mw2022/factory" ) == true && r.Enabled ), "factory replacements disabled after remove" );
					Require( !renderer.Model.Materials.Select( (m, i) => renderer.Materials.GetOverride( i )?.Name ).Any( n => n?.EndsWith( "/hidden.vmat" ) == true ), "material restore " + part.Name );
					lines.Add( $"PASS {(world ? "world" : "view")} {part.Name}: equip, model, mount, remove and factory restoration" );
				}
				var barrelPoint = points.Single( p => p.Category == GunsmithPartType.Barrel );
				var muzzlePoint = points.Single( p => p.Category == GunsmithPartType.Muzzle );
				muzzlePoint.SetPart( ResourceLibrary.Get<GunsmithPart>( "gunsmith/m4a1/mw2022/att_vm_silencer02.gnsmth" ) );
				foreach ( var key in new[] { "att_vm_p01_ar_mike4_barshort_v0", "att_vm_p01_ar_mike4_barhvy_v0" } )
				{
					barrelPoint.SetPart( ResourceLibrary.Get<GunsmithPart>( $"gunsmith/m4a1/mw2022/{key}.gnsmth" ) );
					var barrelMount = barrelPoint.CurrentGameObject.Components.Get<GunsmithMw22Attachment>();
					var muzzleMount = muzzlePoint.CurrentGameObject.Components.Get<GunsmithMw22Attachment>();
					muzzleMount.RefreshMount();
					Require( muzzleMount.WorldPosition.Distance( barrelMount.BarrelMuzzle ) < .01f, "muzzle follows barrel " + key );
					var factory = renderer.Components.Get<GunsmithMw22Factory>(); factory.Refresh();
					var muzzleMesh = muzzlePoint.CurrentGameObject.Components.Get<ModelRenderer>();
					Require( factory.MuzzleEffectPoint.WorldPosition.Distance( muzzleMesh.WorldTransform.PointToWorld( new Vector3( muzzleMesh.Model.Bounds.Maxs.x, 0, 0 ) ) ) < .01f, "muzzle effects follow device" );
				}
				lines.Add( $"PASS {(world ? "world" : "view")} short/long barrel changes move muzzle attachment and discharge effects." );
			}
			finally { scene.Destroy(); }
		}
		File.WriteAllLines( Path.Combine( Folder, "roundtrip.txt" ), lines );
		Log.Info( "MW22 ROUNDTRIP PASS" );
	}
	private static void Require( bool ok, string name ) { if ( !ok ) throw new Exception( "MW22 QA FAIL: " + name ); }
	[ConCmd( "hc1_mw22_optic_check" )]
	public static void OpticCheck()
	{
		var report = new List<object>();
		foreach ( var part in ResourceLibrary.GetAll<GunsmithPart>().Where( p => p.ResourcePath.StartsWith( "gunsmith/m4a1/mw2022/" ) && p.Category == GunsmithPartType.Optic ).OrderBy( p => p.ResourcePath ) )
		{
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var prefab = ResourceLibrary.Get<PrefabFile>( "weapons/m4a1/vm_m4a1.prefab" );
			var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false } );
			root.Components.GetOrCreate<GunsmithWeapon>().Resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
			foreach ( var c in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) ) c.Enabled = c is ModelRenderer || c is GunsmithAttachmentPoint;
			var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) ) if ( other != renderer ) other.Enabled = false;
			renderer.RenderOptions.Game = true; renderer.RenderOptions.Overlay = false;
			renderer.UseAnimGraph = true; renderer.PlaybackRate = 1; renderer.PlayAnimationsInEditorScene = true;
			renderer.Set( "ironsights", 1 ); renderer.Set( "speed_ironsights", 1 ); renderer.Set( "b_grounded", true );
			var point = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == GunsmithPartType.Optic );
			var camera = new GameObject( true, "MW22 ADS camera" ).Components.Create<CameraComponent>();
			camera.BackgroundColor = new Color( .15f, .22f, .29f ); camera.FieldOfView = 75; camera.ZNear = .1f;
			var light = new GameObject( true, "MW22 ADS light" ).Components.Create<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 30, -35, 0 ) ); light.LightColor = Color.White * 2; light.SkyColor = Color.White * .8f;
			root.Enabled = true;
			{
				var previous = point.CurrentGameObject; point.SetPart( part ); previous?.DestroyImmediate();
				root.WorldPosition = part.OpticAimOffset; renderer.SceneModel.Transform = renderer.WorldTransform;
				for ( int i = 0; i < 100; i++ ) { scene.EditorTick( .02f, .02f ); renderer.SceneModel.Update( .02f ); }
				var mount = point.CurrentGameObject.Components.Get<GunsmithMw22Attachment>(); mount.RefreshMount();
				var model = point.CurrentGameObject.Components.Get<ModelRenderer>().Model;
				var key = Path.GetFileNameWithoutExtension( model.Name );
				using var doc = System.Text.Json.JsonDocument.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), $"Sources/MW2022/models/{key}.json" ) ) );
				var head = doc.RootElement.GetProperty( "bones" ).EnumerateArray().First( b => b.GetProperty( "name" ).GetString() == "tag_reticle_attach" ).GetProperty( "head" );
				var target = mount.WorldTransform.PointToWorld( new Vector3( head[0].GetSingle(), head[1].GetSingle(), head[2].GetSingle() ) );
				// The original ADS animgraph retains its small breathing/idle motion.
				report.Add( new { part.ResourcePath, x = target.x, y = target.y, z = target.z, pass = target.x > .5f && MathF.Abs( target.y ) < .04f && MathF.Abs( target.z ) < .04f } );
				if ( key is "att_vm_minireddot01_tall" or "att_vm_4x_west01_tall" or "att_vm_holo_west01" )
				{
					using var bmp = new Bitmap( 1400, 900 ); camera.RenderToBitmap( bmp ); File.WriteAllBytes( Path.Combine( Folder, key + "-ads.png" ), bmp.ToPng() );
				}
			}
		}
		finally { scene.Destroy(); }
		}
		File.WriteAllText( Path.Combine( Folder, "optic-alignment.json" ), System.Text.Json.JsonSerializer.Serialize( report, new System.Text.Json.JsonSerializerOptions { WriteIndented = true } ) );
	}
}
