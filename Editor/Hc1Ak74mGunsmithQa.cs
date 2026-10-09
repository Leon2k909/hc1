using Editor;
using Sandbox;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;

/// <summary>
/// Offscreen checks of the AK-74M's own gunsmith parts on its world model, in a scene of their own each, so they can run
/// beside a match: every stock, pistol grip and magazine fitted through its attachment point, rendered from the right.
/// </summary>
public static class Hc1Ak74mGunsmithQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/ak74m-gunsmith" );

	/// <summary>The factory mask: the brake, the side mount's "off", the stock's release button and the factory parts.</summary>
	private const ulong FactoryMask = 553713749;

	/// <summary>
	/// filter: only parts whose file name contains it ("" for all, "factory" for the bare gun).
	/// view: 0 the stock and grip close up, 1 the whole gun, 2 the magazine close up.
	/// </summary>
	[ConCmd( "hc1_ak74m_parts_check" )]
	public static async void Check( string filter = "", int view = 0 )
	{
		var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/ak74m/ak74m.equip" );
		var paths = new List<string>();
		foreach ( var folder in new[] { "stocks", "pistol_grips", "magazines" } )
			paths.AddRange( Directory.GetFiles( Path.Combine( Project.Current.GetAssetsPath(), "gunsmith/ak74m", folder ), "*.gnsmth" )
				.Select( f => $"gunsmith/ak74m/{folder}/{Path.GetFileName( f )}" ) );
		var parts = new List<GunsmithPart> { null };
		foreach ( var path in paths.Where( p => p.Contains( filter ) ) )
			parts.Add( await ResourceLibrary.LoadAsync<GunsmithPart>( path ) );
		if ( filter.Length > 0 && !"factory".Contains( filter ) ) parts.RemoveAt( 0 );
		Directory.CreateDirectory( Folder );
		var written = 0;
		foreach ( var part in parts )
		{
			try { Render( resource, part, view ); written++; }
			catch ( Exception e ) { Log.Error( e.Message ); }
		}
		Log.Info( $"AK74M_QA wrote {written} of {parts.Count} to {Folder}" );
	}

	private static void Render( EquipmentResource resource, GunsmithPart part, int view )
	{
		// A fresh scene each: an offscreen scene keeps drawing what it first drew where it first drew it.
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var prefab = ResourceLibrary.Get<PrefabFile>( "weapons/ak74m/wm_ak74m.prefab" );
			var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
			foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
				component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
			var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			Require( renderer.Model is not null && !renderer.Model.IsError, "AK-74M world model compiled" );
			Require( (ulong)renderer.BodyGroups == FactoryMask && (ulong)renderer.Model.Parts.DefaultMask == FactoryMask,
				$"prefab {renderer.BodyGroups} and model default {renderer.Model.Parts.DefaultMask} are {FactoryMask}" );
			renderer.UseAnimGraph = false;
			renderer.RenderOptions.Game = true;
			renderer.RenderType = ModelRenderer.ShadowRenderType.On;

			var name = "factory";
			if ( part is not null )
			{
				Require( part.IsValid() && part.Supports( resource ), $"{part.ResourcePath} fits the AK-74M" );
				var point = root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants )
					.Single( p => p.Category == part.Category );
				point.SetPart( part );
				foreach ( var group in part.GetBodygroups( renderer.Model ) )
					Require( renderer.GetBodyGroup( group.Key ) == group.Value, $"{part.Name} sets {group.Key} {group.Value}" );
				name = Path.GetFileNameWithoutExtension( part.ResourcePath ).Replace( "att_vm_p04_", "" );
			}

			root.Enabled = true;
			var camera = new GameObject( true, "AK-74M QA camera" ).AddComponent<CameraComponent>();
			camera.BackgroundColor = new Color( .025f, .03f, .035f );
			camera.FieldOfView = view == 1 ? 34 : 30;
			camera.ZNear = .1f;
			var (center, offset) = view switch
			{
				1 => (new Vector3( 8, 0, 1 ), new Vector3( 5, -92, 13 )),
				2 => (new Vector3( 5, 0, -2 ), new Vector3( 2, -34, 6 )),
				_ => (new Vector3( -6, 0, 1.5f ), new Vector3( 3, -34, 7 )),
			};
			camera.WorldPosition = center + offset;
			camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
			var light = new GameObject( true, "AK-74M QA light" ).AddComponent<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 35, 35, 0 ) );
			light.LightColor = Color.White * 2;
			light.SkyColor = Color.White * .7f;
			scene.EditorTick( .01f, .01f );
			renderer.SceneModel.Update( 0 );
			using var bitmap = new Bitmap( 1200, 700 );
			camera.RenderToBitmap( bitmap, false );
			File.WriteAllBytes( Path.Combine( Folder, $"view{view}-{name}.png" ), bitmap.ToPng() );
		}
		finally { scene.Destroy(); }
	}

	private static void Require( bool condition, string message )
	{
		if ( !condition ) throw new Exception( "AK74M_QA FAIL: " + message );
	}
}
