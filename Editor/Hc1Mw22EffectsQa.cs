using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;

public static class Hc1Mw22EffectsQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "Sources/MW2022/qa" );
	[ConCmd( "hc1_mw22_all_lenses" )]
	public static void AllLenses()
	{
		foreach ( var p in ResourceLibrary.GetAll<GunsmithPart>().Where( p => p.Category == GunsmithPartType.Optic && p.ResourcePath.StartsWith("gunsmith/m4a1/mw2022/") ) )
			LensScene( Path.GetFileNameWithoutExtension(p.ResourcePath), "clear" );
		File.WriteAllText( Path.Combine(Folder,"all-lenses-complete.txt"), DateTime.UtcNow.ToString("O") );
	}
	[ConCmd( "hc1_mw22_laser_check" )]
	public static void LaserCheck()
	{
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var wall = new GameObject( true, "Laser target wall" );
			wall.WorldPosition = new Vector3( 160, 0, 8 );
			var collider = wall.Components.Create<BoxCollider>(); collider.Scale = new Vector3( 4, 80, 60 );
			var wallMesh = wall.Components.Create<ModelRenderer>(); wallMesh.Model = Model.Load("models/dev/box.vmdl"); wallMesh.Tint = new Color(.25f,.3f,.35f);
			wallMesh.LocalScale = new Vector3( .08f, 1.6f, 1.2f );
			// Collider dimensions are independent of the visual target transform.
			collider.Scale = new Vector3( 50, 50, 50 );
			var root = SceneUtility.GetPrefabScene( ResourceLibrary.Get<PrefabFile>( "weapons/m4a1/wm_m4a1.prefab" ) ).Clone( new CloneConfig { StartEnabled = false } );
			root.Components.GetOrCreate<GunsmithWeapon>().Resource = ResourceLibrary.Get<EquipmentResource>("weapons/m4a1/m4a1.equip");
			foreach ( var c in root.Components.GetAll<Component>(FindMode.EverythingInSelfAndDescendants) ) c.Enabled = c is ModelRenderer || c is GunsmithAttachmentPoint;
			var weapon = root.Components.Get<SkinnedModelRenderer>(FindMode.EverythingInSelf); weapon.RenderOptions.Game = true; weapon.RenderOptions.Overlay = false;
			var point = root.Components.GetAll<GunsmithAttachmentPoint>(FindMode.EverythingInSelfAndDescendants).Single(p=>p.Category==GunsmithPartType.Laser);
			root.Enabled = true;
			var beam = new GameObject(true,"Laser test beam").Components.Create<GunsmithLaserBeam>();
			var camera = new GameObject(true,"Laser camera").Components.Create<CameraComponent>();
			camera.WorldPosition = new Vector3( -14,-120,50 ); camera.WorldRotation = Rotation.LookAt(new Vector3(70,0,8)-camera.WorldPosition); camera.FieldOfView=64; camera.BackgroundColor=new Color(.025f,.035f,.055f);
			var light=new GameObject(true,"Laser QA light").Components.Create<DirectionalLight>(); light.WorldRotation=Rotation.From(new Angles(25,30,0));light.LightColor=Color.White*1.5f;light.SkyColor=Color.White*.5f;
			var report = new System.Collections.Generic.List<string>();
			foreach(var id in new[]{"01","02","03"})
			{
				var previous=point.CurrentGameObject;
				point.SetPart(ResourceLibrary.Get<GunsmithPart>($"gunsmith/m4a1/mw2022/att_vm_p01_ar_mike4_laser{id}.gnsmth")); previous?.DestroyImmediate();
				scene.EditorTick(.02f,.02f);
				var mount=point.CurrentGameObject.Components.Get<GunsmithMw22Attachment>();mount.RefreshMount();
				var start=mount.WorldTransform.PointToWorld(mount.LaserEmitter);
				beam.BeamColor=mount.LaserColor;beam.BeamWidth=mount.LaserWidth;
				beam.TraceBeam(start,mount.WorldRotation.Forward,root);
				if(!beam.HasHit || MathF.Abs(beam.End.x-158)>.05f)throw new Exception($"laser {id} missed wall: {beam.End} hit={beam.HasHit}");
				using var bmp=new Bitmap(1400,800);camera.RenderToBitmap(bmp);File.WriteAllBytes(Path.Combine(Folder,$"laser-{id}.png"),bmp.ToPng());
				report.Add($"PASS laser {id}: emitter={start} colour={beam.BeamColor} wall hit={beam.End}");
				beam.TraceBeam(start,Vector3.Backward,root);
				if(beam.HasHit || MathF.Abs(beam.Start.Distance(beam.End)-beam.Range)>.05f)throw new Exception("no-hit range/dot");
				beam.Hide();if(beam.IsVisible || beam.HasHit)throw new Exception("hide leaves beam/dot");
			}
			beam.Enabled=false;if(beam.IsVisible)throw new Exception("disable leaves scene object");
			report.Add("PASS no-hit range, hit-dot removal, hide and disable cleanup.");
			File.WriteAllLines(Path.Combine(Folder,"laser-check.txt"),report);
		}
		finally { scene.Destroy(); }
	}
	[ConCmd( "hc1_mw22_lens_scene" )]
	public static void LensScene( string key = "att_vm_4x_west01_tall", string suffix = "before", bool hideGlass = false, bool overlay = true )
	{
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var part = ResourceLibrary.Get<GunsmithPart>( $"gunsmith/m4a1/mw2022/{key}.gnsmth" );
			var root = SceneUtility.GetPrefabScene( ResourceLibrary.Get<PrefabFile>( "weapons/m4a1/vm_m4a1.prefab" ) ).Clone( new CloneConfig { StartEnabled = false } );
			root.Components.GetOrCreate<GunsmithWeapon>().Resource = ResourceLibrary.Get<EquipmentResource>( "weapons/m4a1/m4a1.equip" );
			foreach ( var c in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) ) c.Enabled = c is ModelRenderer || c is GunsmithAttachmentPoint;
			var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) ) if ( other != renderer ) other.Enabled = false;
			renderer.RenderOptions.Game = !overlay; renderer.RenderOptions.Overlay = overlay;
			renderer.UseAnimGraph = true; renderer.PlaybackRate = 1; renderer.PlayAnimationsInEditorScene = true;
			renderer.Set( "ironsights", 1 ); renderer.Set( "speed_ironsights", 1 ); renderer.Set( "b_grounded", true );
			var point = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == GunsmithPartType.Optic );
			point.SetPart( part ); root.WorldPosition = part.OpticAimOffset;
			root.Enabled = true; renderer.SceneModel.Transform = renderer.WorldTransform;
			for ( int i = 0; i < 100; i++ ) { scene.EditorTick( .02f, .02f ); renderer.SceneModel.Update( .02f ); }
			point.CurrentGameObject.Components.Get<GunsmithMw22Attachment>().RefreshMount();
			var optic = point.CurrentGameObject.Components.Get<ModelRenderer>();
			File.WriteAllLines( Path.Combine( Folder, key + "-materials.txt" ), optic.Model.Materials.Select( (m,i) => $"{i}: {m.Name} override={optic.Materials.GetOverride(i)?.Name}" ).Append( $"mask={optic.BodyGroups} parts={string.Join("|", optic.Model.Parts.All.Select(p=>p.Name+":"+p.Mask))}" ) );
			if ( hideGlass ) for ( int i = 0; i < optic.Model.Materials.Length; i++ )
				if ( optic.Model.Materials[i].Name.Contains("lens") || optic.Model.Materials[i].Name.Contains("reticle") ) optic.Materials.SetOverride( i, Material.Load( "attachments/m4a1/materials/hidden.vmat" ) );
			var camera = new GameObject( true, "Lens world camera" ).Components.Create<CameraComponent>();
			camera.BackgroundColor = new Color( .1f, .2f, .4f ); camera.FieldOfView = 50; camera.ZNear = .1f;
			var box = Model.Load( "models/dev/box.vmdl" );
			if ( box.IsError ) throw new Exception( "QA backdrop model missing" );
			for ( int y = -3; y <= 3; y++ ) for ( int z = -3; z <= 3; z++ )
			{
				var tile = new GameObject( true, "World checker tile" ).Components.Create<ModelRenderer>();
				tile.Model = box; tile.WorldPosition = new Vector3( 200, y * 25, z * 25 ); tile.WorldScale = new Vector3( .05f, .25f, .25f );
				tile.Tint = (y + z) % 2 == 0 ? new Color( .95f, .8f, .35f ) : new Color( .12f, .5f, .75f );
			}
			var light = new GameObject( true, "Lens QA light" ).Components.Create<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 30, 30, 0 ) ); light.LightColor = Color.White * 2; light.SkyColor = Color.White;
			scene.EditorTick( .01f, .01f );
			using var bmp = new Bitmap( 1400, 900 );
			camera.RenderToBitmap( bmp ); File.WriteAllBytes( Path.Combine( Folder, $"{key}-world-{suffix}.png" ), bmp.ToPng() );
			root.DestroyImmediate();
			using var reference = new Bitmap(1400,900);
			camera.RenderToBitmap( reference ); File.WriteAllBytes( Path.Combine( Folder, $"{key}-world-reference.png" ), reference.ToPng() );
		}
		finally { scene.Destroy(); }
	}
	[ConCmd( "hc1_mw22_effects_info" )]
	public static void Info()
	{
		Directory.CreateDirectory( Folder );
		var lines = new System.Collections.Generic.List<string>();
		foreach ( var type in new[] { typeof(SceneLineObject), typeof(SceneObject), typeof(Model), typeof(CameraComponent) } )
			lines.AddRange( type.GetMembers( System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static ).Select( m => type.Name + " " + m ) );
		var scene = Game.ActiveScene;
		if ( scene.IsValid() ) foreach ( var p in scene.GetAllComponents<GunsmithAttachmentPoint>().Where( p => p.Category is GunsmithPartType.Optic or GunsmithPartType.Laser ) )
			lines.Add( $"LIVE {p.Category}: {p.CurrentPart?.ResourcePath} root={p.GameObject.Root.Name}" );
		File.WriteAllLines( Path.Combine( Folder, "effects-info.txt" ), lines );
	}
	[ConCmd( "hc1_mw22_shader" )]
	public static async System.Threading.Tasks.Task CompileShader() => await EditorUtility.CompileShader( "shaders/m4_optic_lens.shader", new(), default );
}
