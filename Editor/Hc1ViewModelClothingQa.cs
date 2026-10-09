using Editor;
using Sandbox;
using Facepunch;
using System;
using System.IO;
using System.Linq;
using System.Reflection;

/// <summary>
/// <c>hc1_vm_clothing [weapon] [style] [view]</c>: renders a ported gun's viewmodel offscreen with the first-person
/// clothing (<see cref="ViewModelClothing"/>) from the eye, at the hip, aimed and through an aimed reload, into
/// <c>output/vm-clothing/</c>, and logs every clothing vertex-bearing bone that comes within 6 of the eye.
/// view 0 is the eye (the camera bone), 1 a look from behind and above the eye, 2 from its left and 3 from its right.
/// </summary>
public static class Hc1ViewModelClothingQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/vm-clothing" );

	// Pose name, ironsights weight, seconds into a reload (negative: none).
	private static readonly (string Name, float Aim, float Reload)[] Poses =
	{
		("hip", 0f, -1f),
		("ads", 1f, -1f),
		("ads-reload-0.3", 1f, 0.3f),
		("ads-reload-0.6", 1f, 0.6f),
		("ads-reload-0.9", 1f, 0.9f),
		("ads-reload-1.2", 1f, 1.2f),
		("hip-reload-0.6", 0f, 0.6f),
	};

	[ConCmd( "hc1_vm_clothing" )]
	public static void Run( string weapon = "m18", int style = 0, int view = 0 )
	{
		Directory.CreateDirectory( Folder );
		var written = 0;
		foreach ( var pose in Poses )
		{
			try { Render( weapon, (MilitaryUniformStyle)style, pose.Name, pose.Aim, pose.Reload, view ); written++; }
			catch ( Exception e ) { Log.Error( "VMCLOTH " + e ); }
		}
		Log.Info( $"VMCLOTH wrote {written} of {Poses.Length} to {Folder}" );
	}

	private static void Render( string weapon, MilitaryUniformStyle style, string name, float aim, float reload, int view )
	{
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/{weapon}/vm_{weapon}.prefab" );
			if ( prefab is null ) throw new Exception( $"no weapons/{weapon}/vm_{weapon}.prefab" );
			var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
			foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
				component.Enabled = component is ModelRenderer;
			var gun = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			SkinnedModelRenderer arms = null;
			foreach ( var r in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInDescendants ) )
				if ( r.Model?.Name?.Contains( "first_person_arms" ) == true ) arms = r;
			if ( arms is null ) throw new Exception( "no first-person arms" );
			foreach ( var r in root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				r.RenderOptions.Game = true;
				r.RenderOptions.Overlay = false;
			}

			// The body the clothing copies, well out of view.
			var bodyObject = new GameObject( true, "Body" );
			bodyObject.WorldPosition = new Vector3( 0, 0, -5000 );
			var body = bodyObject.AddComponent<SkinnedModelRenderer>( false );
			body.Model = Model.Load( MilitaryUniform.HumanModelPath );
			var uniform = bodyObject.AddComponent<MilitaryUniform>( false );
			var source = SceneUtility.GetPrefabScene( ResourceLibrary.Get<PrefabFile>( "prefabs/player/player.prefab" ) )
				.Components.Get<MilitaryUniform>( FindMode.EverythingInSelfAndDescendants );
			uniform.Style = style;
			if ( source is not null )
			{
				uniform.Pieces = source.Pieces.ToList();
				uniform.FieldPieces = source.FieldPieces.ToList();
				uniform.TacticalPieces = source.TacticalPieces.ToList();
			}

			root.Enabled = true;
			var clothing = root.AddComponent<ViewModelClothing>();
			clothing.Arms = arms;
			clothing.Body = body;
			typeof( ViewModelClothing ).GetMethod( "Dress", BindingFlags.NonPublic | BindingFlags.Instance )
				.Invoke( clothing, new object[] { uniform } );

			// Run the gun's graph to the pose.
			var model = gun.SceneModel;
			model.SetAnimParameter( "b_deploy_skip", 1 );
			model.SetAnimParameter( "ironsights_weight", aim );
			const float step = 1f / 60f;
			for ( int i = 0; i < 90; i++ ) model.Update( step );
			if ( reload >= 0 )
			{
				model.SetAnimParameter( "b_reload", 1 );
				for ( float t = 0; t < reload; t += step ) model.Update( step );
			}
			arms.SceneModel.MergeBones( model );

			// The garments' SceneModels come in on the scene's first tick.
			scene.EditorTick( .01f, .01f );
			var eye = model.GetBoneWorldTransform( "camera" );
			typeof( ViewModelClothing ).GetMethod( "Apply", BindingFlags.NonPublic | BindingFlags.Instance )
				.Invoke( clothing, new object[] { eye } );

			var camera = new GameObject( true, "Eye" ).AddComponent<CameraComponent>();
			camera.BackgroundColor = new Color( .3f, .35f, .4f );
			// Not a main camera, so the clothing keeps the eye's pose rather than following this one.
			camera.IsMainCamera = false;
			camera.FieldOfView = aim > 0 ? 80 : 85;
			camera.ZNear = 1f;
			var from = view switch
			{
				1 => eye.PointToWorld( new Vector3( -40, 0, 22 ) ),
				2 => eye.PointToWorld( new Vector3( 4, 40, 0 ) ),
				3 => eye.PointToWorld( new Vector3( 4, -40, 0 ) ),
				_ => eye.Position,
			};
			camera.WorldPosition = from;
			camera.WorldRotation = view == 0 ? eye.Rotation : Rotation.LookAt( eye.Position + eye.Forward * 6 - from );
			var light = new GameObject( true, "Light" ).AddComponent<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 50, 30, 0 ) );
			light.LightColor = Color.White * 2;
			light.SkyColor = Color.White * .8f;

			// Which garment bones come near the eye.
			var report = new System.Text.StringBuilder();
			foreach ( var r in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInDescendants ) )
			{
				if ( r == arms || r == gun || !r.Enabled || r.Model is null || !r.SceneModel.IsValid() ) continue;
				if ( r.GameObject == arms.GameObject ) continue;
				var nearest = float.MaxValue;
				var nearestBone = "";
				for ( int b = 0; b < r.Model.BoneCount; b++ )
				{
					var p = eye.PointToLocal( r.SceneModel.GetBoneWorldTransform( b ).Position );
					var d = p.Length;
					if ( d < nearest ) { nearest = d; nearestBone = r.Model.GetBoneName( b ) + " " + p; }
				}
				report.Append( $" [{Path.GetFileNameWithoutExtension( r.Model.Name )}: {nearestBone} {nearest:0.0}]" );
			}
			Log.Info( $"VMCLOTH {weapon} {name}:{report}" );

			scene.EditorTick( .01f, .01f );
			using var bitmap = new Bitmap( 1280, 720 );
			camera.RenderToBitmap( bitmap, false );
			File.WriteAllBytes( Path.Combine( Folder, $"{weapon}-{style}-{name}-v{view}.png" ), bitmap.ToPng() );
		}
		finally { scene.Destroy(); }
	}
}
