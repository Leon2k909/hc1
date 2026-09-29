using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;

/// <summary>
/// Offscreen checks of the FN FAL's own gunsmith parts (the Para stock, the 18-inch barrel and the 30-round magazine),
/// in a scene of their own, so they can run beside a match.
/// </summary>
public static class Hc1FalGunsmithQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/fal-gunsmith" );

	private static readonly string[] PartPaths =
	{
		"gunsmith/fal/stocks/att_vm_p04_para.gnsmth",
		"gunsmith/fal/barrels/att_vm_p04_short.gnsmth",
		"gunsmith/fal/magazines/att_vm_p04_xmag.gnsmth",
	};

	private const int FactoryMask = 174761;
	private static readonly Vector3 ShortMuzzleShift = new( -2.099f, 0, 0.002f );
	private static readonly Vector3 ShortBareMuzzle = new( -5.926f, 0, 0 );

	/// <summary>
	/// Fits and removes each part, checks the bodygroups, the muzzle tip and the discharge point, then renders.
	/// variant: 0 factory, 1 the three parts, 2 those and a suppressor, 3 those and a charm.
	/// view: 0 the whole gun from the right, 1 from the left, 2 the charm close up, 3 the muzzle close up, 4 the charm's
	/// hook from above.
	/// A viewmodel (world 0) renders from its own camera at <paramref name="pose"/>'s <paramref name="cycle"/>.
	/// </summary>
	[ConCmd( "hc1_fal_parts_check" )]
	public static async void Check( bool world = true, int variant = 1, string pose = "idle", float cycle = 0, int view = 0 )
	{
		// Load first, with no scene pushed: a scene pushed across an await stays the active scene for the frames in
		// between, where a running match would find it instead of its own.
		var parts = new List<GunsmithPart>();
		foreach ( var path in PartPaths ) parts.Add( await ResourceLibrary.LoadAsync<GunsmithPart>( path ) );
		var charm = await ResourceLibrary.LoadAsync<GunsmithPart>( "gunsmith/charms/charm_fp.gnsmth" );
		try { Run( world, variant, pose, cycle, view, parts, charm ); }
		catch ( Exception e ) { Log.Error( e.Message ); }
	}

	private static void Run( bool world, int variant, string pose, float cycle, int view, List<GunsmithPart> parts, GunsmithPart charm )
	{
		Directory.CreateDirectory( Folder );
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var prefab = ResourceLibrary.Get<PrefabFile>( $"weapons/fal/{(world ? "wm" : "vm")}_fal.prefab" );
			var root = SceneUtility.GetPrefabScene( prefab ).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
			foreach ( var component in root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
				component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
			var renderer = root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			Require( renderer.Model is not null && !renderer.Model.IsError, "FAL model compiled" );
			Require( renderer.Model.Materials.All( m => !m.Name.Contains( "error" ) ), "materials resolved" );
			renderer.UseAnimGraph = false;
			var prefabMask = renderer.BodyGroups;
			Require( prefabMask == FactoryMask && (ulong)renderer.Model.Parts.DefaultMask == FactoryMask,
				$"prefab {prefabMask} and model default {renderer.Model.Parts.DefaultMask} are the documented {FactoryMask}" );
			renderer.BodyGroups = 0;
			foreach ( var group in renderer.Model.Parts.All ) renderer.SetBodyGroup( group.Name, 0 );
			// Choosing each group's first choice leaves out the default's bits for empty choices (optic_rail's,
			// laser_rail's and sight_folded's "off"), which have no meshes, so it draws the same gun.
			var factory = renderer.BodyGroups;
			ulong meshed = 0;
			foreach ( var group in renderer.Model.Parts.All ) meshed |= (ulong)group.Mask;
			var missing = (ulong)FactoryMask & ~(ulong)factory;
			Require( ((ulong)factory & ~(ulong)FactoryMask) == 0 && (missing & meshed) == 0,
				$"first choices {factory} are the default {FactoryMask} less bits {missing} that no mesh uses" );
			if ( !world )
				foreach ( var clip in new[] { "reload_xmag", "reload_empty_xmag" } )
					Require( Enumerable.Range( 0, renderer.Model.AnimationCount ).Any( i => renderer.Model.GetAnimationName( i ) == clip ), "viewmodel has " + clip );

			renderer.RenderOptions.Game = true;
			renderer.RenderOptions.Overlay = false;
			renderer.RenderType = ModelRenderer.ShadowRenderType.On;
			renderer.PlayAnimationsInEditorScene = true;
			renderer.Sequence.Name = world ? "idle" : pose;
			renderer.PlaybackRate = 0;
			foreach ( var other in root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				if ( other != renderer ) { other.Enabled = !world; other.RenderOptions.Game = true; other.RenderOptions.Overlay = false; }

			var resource = ResourceLibrary.Get<EquipmentResource>( "weapons/fal/fal.equip" );
			for ( var i = 0; i < PartPaths.Length; i++ )
			{
				Require( parts[i].IsValid(), "loaded " + PartPaths[i] );
				Require( parts[i].Supports( resource ), parts[i].Name + " fits the FAL" );
			}
			var stock = parts[0];
			var barrel = parts[1];
			var magazine = parts[2];
			Require( Near( stock.VerticalRecoilScale, 1.05f ) && Near( stock.HorizontalRecoilScale, 1.05f ), "Para stock: 5% more recoil" );
			Require( Near( barrel.DamageFalloffScale, 0.95f ), "18-inch barrel: falloff 0.95" );
			Require( magazine.MagazineCapacity == 30 && magazine.ReloadAnimation == 1 && Near( magazine.ReloadTime, 2.67f )
				&& Near( magazine.EmptyReloadTime, 3.57f ) && magazine.ReloadSounds.Count > 0 && magazine.EmptyReloadSounds.Count > 0,
				"30-round magazine: capacity, reload clips, times and sounds" );
			Require( Near( Effects( barrel ).DamageFalloffDistance, 0.95f ), "the barrel's falloff reaches the shot effects" );
			Require( Near( Effects( stock ).VerticalRecoil, 1.05f ) && Near( Effects( stock ).HorizontalRecoil, 1.05f ), "the stock's recoil reaches the shot effects" );

			GunsmithAttachmentPoint Point( GunsmithPartType category ) =>
				root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).Single( p => p.Category == category );
			foreach ( var part in parts )
			{
				var point = Point( part.Category );
				var original = renderer.BodyGroups;
				point.SetPart( part );
				foreach ( var group in part.GetBodygroups( renderer.Model ) )
					Require( renderer.GetBodyGroup( group.Key ) == group.Value, $"{part.Name} sets {group.Key} {group.Value}" );
				point.SetPart( null );
				Require( renderer.BodyGroups == original, $"factory restored after {part.Name}" );
			}

			// The factory barrel: a device hides its flash hider, and the shots leave the factory muzzle.
			var muzzle = Point( GunsmithPartType.Muzzle );
			var suppressor = ResourceLibrary.GetAll<GunsmithPart>().First( p => p.Category == GunsmithPartType.Muzzle && p.IsSuppressor && p.Supports( resource ) );
			Require( GunsmithAttachmentPoint.DischargeShift( root ) == Vector3.Zero, "factory barrel: no discharge shift" );
			muzzle.SetPart( suppressor );
			Require( renderer.GetBodyGroup( "muzzle_tip" ) == 2, "a device hides the factory flash hider" );
			Require( GunsmithAttachmentPoint.MuzzleShift( root ) == Vector3.Zero, "factory barrel: device on the factory mount" );
			muzzle.SetPart( null );
			Require( renderer.GetBodyGroup( "muzzle_tip" ) == 0, "removing the device restores the factory flash hider" );

			// The 18-inch barrel: its own short flash hider, a device mounted 2.1 back, and the bare muzzle 5.9 back.
			Point( GunsmithPartType.Barrel ).SetPart( barrel );
			Require( renderer.GetBodyGroup( "barrel" ) == 1 && renderer.GetBodyGroup( "muzzle_tip" ) == 1, "18-inch barrel with its short flash hider" );
			Require( Near( GunsmithAttachmentPoint.MuzzleShift( root ), ShortMuzzleShift ), "device mount: " + GunsmithAttachmentPoint.MuzzleShift( root ) );
			Require( Near( GunsmithAttachmentPoint.DischargeShift( root ), ShortBareMuzzle ), "bare muzzle: " + GunsmithAttachmentPoint.DischargeShift( root ) );
			muzzle.SetPart( suppressor );
			Require( renderer.GetBodyGroup( "muzzle_tip" ) == 2, "a device hides the short flash hider" );
			Require( Near( GunsmithAttachmentPoint.DischargeShift( root ), ShortMuzzleShift ), "shots leave the device: " + GunsmithAttachmentPoint.DischargeShift( root ) );
			muzzle.SetPart( null );
			Require( renderer.GetBodyGroup( "muzzle_tip" ) == 1, "removing the device restores the short flash hider" );
			Point( GunsmithPartType.Barrel ).SetPart( null );
			Require( renderer.BodyGroups == factory, "factory restored after the barrel checks" );

			if ( variant > 0 )
				foreach ( var part in parts ) Point( part.Category ).SetPart( part );
			if ( variant == 2 ) muzzle.SetPart( suppressor );
			if ( variant == 3 )
				Point( GunsmithPartType.Charm ).SetPart( charm );

			root.Enabled = true;
			renderer.Sequence.TimeNormalized = cycle;
			var camera = new GameObject( true, "FAL QA camera" ).AddComponent<CameraComponent>();
			camera.BackgroundColor = new Color( .025f, .03f, .035f );
			camera.FieldOfView = world ? 34 : 80;
			camera.ZNear = .1f;
			if ( world )
			{
				var (center, offset) = view switch
				{
					1 => (new Vector3( 4, 0, 2 ), new Vector3( 5, 92, 13 )),
					2 => (new Vector3( -11, 1.5f, 2 ), new Vector3( 6, 26, 8 )),
					3 => (new Vector3( 19, 0, 4.5f ), new Vector3( 3, -24, 5 )),
					4 => (new Vector3( -11, 0.8f, 4.5f ), new Vector3( 4, 6, 24 )),
					_ => (new Vector3( 4, 0, 2 ), new Vector3( 5, -92, 13 )),
				};
				camera.WorldPosition = center + offset;
				camera.WorldRotation = Rotation.LookAt( center - camera.WorldPosition );
			}
			var light = new GameObject( true, "FAL QA light" ).AddComponent<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 35, view is 1 or 2 or 4 ? -35 : 35, 0 ) );
			light.LightColor = Color.White * 2;
			light.SkyColor = Color.White * .7f;
			scene.EditorTick( .01f, .01f );
			renderer.SceneModel.Update( 0 );
			if ( !world )
				foreach ( var arms in root.GetComponentsInChildren<SkinnedModelRenderer>( true ).Where( r => r != renderer ) )
					arms.SceneModel.MergeBones( renderer.SceneModel );
			foreach ( var mount in root.GetComponentsInChildren<GunsmithMw22Attachment>( true ) ) mount.RefreshMount();
			using var bitmap = new Bitmap( 1600, 900 );
			camera.RenderToBitmap( bitmap, false );
			var name = $"{(world ? "world" : "view")}-{variant}-{(world ? $"view{view}" : $"{pose}-{cycle:0.00}")}.png";
			File.WriteAllBytes( Path.Combine( Folder, name ), bitmap.ToPng() );
			Log.Info( $"FAL_QA PASS: three parts fit and reset, factory mask {FactoryMask}, muzzle tips, device mount and discharge point; wrote {name}" );
		}
		finally { scene.Destroy(); }
	}

	/// <summary>A part's shot effects, through the same rules a match applies (standing).</summary>
	private static GunsmithAttachmentEffects Effects( GunsmithPart part )
	{
		object effects = GunsmithAttachmentEffects.ForBuild( null );
		typeof( GunsmithAttachmentEffects ).GetMethod( "Apply", BindingFlags.Instance | BindingFlags.NonPublic )
			.Invoke( effects, new object[] { part, false } );
		return (GunsmithAttachmentEffects)effects;
	}

	private static bool Near( float a, float b ) => Math.Abs( a - b ) < .001f;
	private static bool Near( Vector3 a, Vector3 b ) => a.Distance( b ) < .002f;

	private static void Require( bool condition, string message )
	{
		if ( !condition ) throw new Exception( "FAL_QA FAIL: " + message );
	}
}
