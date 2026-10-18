using Editor;
using Sandbox;
using Facepunch;
using Facepunch.Gunsmith;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

/// <summary>
/// The M16A4 with an optic, in isolated scenes. Never edits the open scene.
/// <para>
/// hc1_m16_optic_check [optic] [label]: an optic takes off the carry handle and leaves the front sight post up, on the
/// view and world models, as on the real rifle, whose front sight base is part of the barrel. A replacement barrel's own
/// folding sight folds under an optic, and taking the optic off puts back whatever the barrel doesn't replace. Renders the
/// aimed view as the game places it (the optic's aim offset, the M16's correction and the optic's sight line, in the
/// "ads" pose), a close-up round the dot, and the world model from its right and from behind, into
/// output/m16-gunsmith/optic-&lt;optic&gt;[-label]-*.png, and checks the dot is on the screen's centre and on the post
/// tip (absolute co-witness) or <see cref="LowerThirdDrop"/> over it (lower 1/3).
/// </para>
/// <para>
/// hc1_m16_cowitness [optic|all]: for each 1x optic, where its dot and the post tip show from the aimed eye, rendered,
/// and the sight line (ManualOffset.OpticSightLines) for either co-witness, into output/m16-gunsmith/cowitness*.
/// </para>
/// </summary>
public static class Hc1M16OpticQa
{
	private static string Folder => Path.Combine( Project.Current.GetRootPath(), "output/m16-gunsmith" );

	private const string M16 = "weapons/m16/m16.equip";
	/// <summary> The top of the front sight post, on the view model's tag_barrel_attach (from the barrel's mesh). </summary>
	private static readonly Vector3 PostTip = new( 13.872f, 0f, 1.522f );
	/// <summary>
	/// Lower 1/3 co-witness: a real optic's line of sight sits 1.535-1.57" over the rail against 1.41" at absolute, so
	/// the post tip shows about this far (inches) under the dot, at the post.
	/// </summary>
	private const float LowerThirdDrop = 0.14f;
	/// <summary> How close (degrees) the dot has to be to where it should be. </summary>
	private const float Tolerance = 0.02f;
	private const float ZoomFov = 9f;
	private const int Width = 1600;
	private const int Height = 900;

	[ConCmd( "hc1_m16_optic_check" )]
	public static async void Check( string optic = "att_vm_reflex_02", string label = "" )
	{
		Directory.CreateDirectory( Folder );
		var name = string.IsNullOrEmpty( label ) ? optic : $"{optic}-{label}";
		var report = new List<string>();
		try
		{
			var resource = await ResourceLibrary.LoadAsync<EquipmentResource>( M16 );
			var part = await ResourceLibrary.LoadAsync<GunsmithPart>( $"gunsmith/m4a1/mw2022/{optic}.gnsmth" );
			var barrel = await ResourceLibrary.LoadAsync<GunsmithPart>( "gunsmith/m16/att_vm_p01_ar_mike4_barhvy_v0.gnsmth" );
			Require( resource.IsValid() && part.IsValid() && part.Category == GunsmithPartType.Optic && part.Supports( resource ), $"{optic} fits the M16" );
			Require( barrel.IsValid() && barrel.Supports( resource ), "a replacement barrel fits the M16" );
			foreach ( var world in new[] { false, true } )
				Fit( resource, part, barrel, world, name, report );
		}
		catch ( Exception e ) { report.Add( "FAIL " + e ); }
		report.Add( report.Any( x => x.StartsWith( "FAIL" ) ) ? "FAILED" : "PASS all checks" );
		File.WriteAllLines( Path.Combine( Folder, $"optic-{name}.txt" ), report );
		foreach ( var line in report )
			Log.Info( $"HC1_M16_OPTIC {line}" );
	}

	private static void Fit( EquipmentResource resource, GunsmithPart optic, GunsmithPart barrel, bool world, string name, List<string> report )
	{
		var mode = world ? "world" : "view";
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var rig = new Rig( scene, resource, world );
			var renderer = rig.Renderer;
			void Expect( string state, string group, int value )
			{
				var actual = renderer.GetBodyGroup( group );
				report.Add( $"{(actual == value ? "PASS" : "FAIL")} {mode} {state}: {group}={actual}, wanted {value}" );
			}
			void ExpectBarrelSight( string state, int value )
			{
				var mesh = rig.BarrelPoint.CurrentGameObject?.Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
				if ( mesh?.Model is null || !mesh.Model.Parts.All.Any( p => p.Name == "sight" ) )
				{
					report.Add( $"NOTE {mode} {state}: the replacement barrel has no front sight group" );
					return;
				}
				var actual = mesh.GetBodyGroup( "sight" );
				report.Add( $"{(actual == value ? "PASS" : "FAIL")} {mode} {state}: the replacement barrel's sight={actual}, wanted {value}" );
			}
			void ExpectFactory( string state )
			{
				report.Add( $"{(renderer.BodyGroups == rig.FactoryBodyGroups ? "PASS" : "FAIL")} {mode} {state}: mask={renderer.BodyGroups}, factory {rig.FactoryBodyGroups}" );
			}
			void Render( string file, Vector3 position, Rotation rotation, float fov, Vector3? mark )
			{
				using var bitmap = rig.Shoot( position, rotation, fov );
				if ( mark is { } point )
				{
					bitmap.SetAntialias( true );
					bitmap.SetFill( Color.Transparent );
					bitmap.SetPen( Color.Cyan, 2 );
					bitmap.DrawCircle( ToPixel( point, position, rotation, fov ), 16 );
				}
				File.WriteAllBytes( Path.Combine( Folder, $"optic-{name}-{file}.png" ), bitmap.ToPng() );
			}

			// The factory barrel with the optic: what the user aimed through.
			rig.OpticPoint.SetPart( optic );
			rig.Settle();
			Expect( "optic", "carry_handle", 1 );
			Expect( "optic", "factory_front_sight", 0 );
			if ( !world )
			{
				var line = rig.SightLineFor( optic );
				report.Add( line is null
					? $"NOTE view: no sight line for {optic.ResourceName} among the M16's {rig.SightLineCount}"
					: $"NOTE view: sight line Position \"{Format( line.Position )}\" Angles \"{Format( line.Angles )}\"" );
				rig.Aim( optic, line?.Position ?? Vector3.Zero, line?.Angles ?? Angles.Zero );
				var seen = rig.Measure();
				report.Add( $"NOTE view: {seen}" );
				var off = MathF.Sqrt( seen.DotUp * seen.DotUp + seen.DotLeft * seen.DotLeft ).RadianToDegree();
				report.Add( $"{(off < Tolerance ? "PASS" : "FAIL")} view: the dot is {off:0.000} degrees from the screen's centre" );
				var slack = Tolerance.DegreeToRadian() * seen.TipDistance;
				var drop = seen.TipDrop;
				var cowitness = MathF.Abs( drop ) < slack ? "absolute co-witness"
					: MathF.Abs( drop - LowerThirdDrop ) < slack ? "lower 1/3 co-witness" : null;
				report.Add( $"{(cowitness is not null ? "PASS" : "FAIL")} view: the post tip is {drop:0.000}\" under the dot at the post{(cowitness is null ? "" : $": {cowitness}")}" );
				var reticle = rig.ReticleTag();
				Render( "ads", rig.EyePosition, rig.EyeRotation, 75, reticle );
				Render( "ads-zoom", rig.EyePosition, rig.LookFromEye( reticle ), ZoomFov, reticle );
			}
			else
			{
				var center = renderer.Model.Bounds.Center;
				Render( "world-right", center + new Vector3( 7, -80, 15 ), Rotation.LookAt( new Vector3( -7, 80, -15 ) ), 34, null );
				var behind = center + new Vector3( -40, -14, 16 );
				Render( "world-behind", behind, Rotation.LookAt( center + new Vector3( 10, 0, 3 ) - behind ), 40, null );
			}

			var previous = rig.OpticPoint.CurrentGameObject;
			rig.OpticPoint.SetPart( null );
			previous?.DestroyImmediate();
			rig.Settle();
			ExpectFactory( "optic off" );

			// A replacement barrel takes the front sight base with it; its own folding sight folds under the optic.
			rig.BarrelPoint.SetPart( barrel );
			rig.OpticPoint.SetPart( optic );
			rig.Settle();
			Expect( "replacement barrel and optic", "factory_front_sight", 1 );
			Expect( "replacement barrel and optic", "carry_handle", 1 );
			ExpectBarrelSight( "replacement barrel and optic", 1 );

			previous = rig.OpticPoint.CurrentGameObject;
			rig.OpticPoint.SetPart( null );
			previous?.DestroyImmediate();
			rig.Settle();
			Expect( "replacement barrel, optic off", "factory_front_sight", 1 );
			Expect( "replacement barrel, optic off", "carry_handle", 0 );
			ExpectBarrelSight( "replacement barrel, optic off", 0 );

			previous = rig.BarrelPoint.CurrentGameObject;
			rig.BarrelPoint.SetPart( null );
			previous?.DestroyImmediate();
			rig.Settle();
			ExpectFactory( "barrel off" );
		}
		catch ( Exception e ) { report.Add( $"FAIL {mode}: {e}" ); }
		finally { scene.Destroy(); }
	}

	/// <summary>
	/// For each 1x optic (or the one named): where the dot and the post tip show from the aimed eye with no sight line,
	/// then the sight line that puts the dot on the screen's centre with the post tip on it (absolute co-witness) and
	/// <see cref="LowerThirdDrop"/> under it (lower 1/3), refined by rendering until it's within a few thousandths of a
	/// degree. Writes cowitness.txt, the lines ready for Tools/kastov_prefabs.py, and before/after views (20 degrees wide,
	/// ticks at the edges marking the screen's centre).
	/// </summary>
	[ConCmd( "hc1_m16_cowitness" )]
	public static async void Cowitness( string optic = "all" )
	{
		Directory.CreateDirectory( Folder );
		var report = new List<string>();
		try
		{
			var resource = await ResourceLibrary.LoadAsync<EquipmentResource>( M16 );
			Require( resource.IsValid(), "the M16 loads" );
			var optics = optic == "all"
				? ResourceLibrary.GetAll<GunsmithPart>()
					.Where( x => x.Category == GunsmithPartType.Optic && x.OverrideAimOffset && x.OpticMagnification <= 1f && x.Supports( resource ) )
					.OrderBy( x => x.ResourceName ).ToList()
				: new List<GunsmithPart> { await ResourceLibrary.LoadAsync<GunsmithPart>( $"gunsmith/m4a1/mw2022/{optic}.gnsmth" ) };
			Require( optics.Count > 0 && optics.All( x => x.IsValid() ), $"{optic} loads" );
			foreach ( var part in optics )
			{
				Solve( resource, part, report );
				// A frame for the editor, and any match in it, between optics.
				await GameTask.DelayRealtime( 50 );
			}
		}
		catch ( Exception e ) { report.Add( "FAIL " + e ); }
		report.Add( report.Any( x => x.StartsWith( "FAIL" ) ) ? "FAILED" : "PASS all solved" );
		var file = optic == "all" ? "cowitness.txt" : $"cowitness-{optic}.txt";
		File.WriteAllLines( Path.Combine( Folder, file ), report );
		foreach ( var line in report )
			Log.Info( $"HC1_M16_COWITNESS {line}" );
	}

	private static void Solve( EquipmentResource resource, GunsmithPart optic, List<string> report )
	{
		var scene = new Scene();
		try
		{
			using var scope = scene.Push();
			var rig = new Rig( scene, resource, false );
			rig.OpticPoint.SetPart( optic );
			rig.Settle();
			Require( rig.Renderer.GetBodyGroup( "factory_front_sight" ) == 0, $"the front sight post is up under {optic.ResourceName}" );
			rig.Aim( optic, Vector3.Zero, Angles.Zero );
			var before = rig.Measure();
			report.Add( $"{optic.ResourceName} before: {before}" );
			rig.Save( $"cowitness-{optic.ResourceName}-before" );

			foreach ( var (label, drop) in new[] { ("absolute", 0f), ("lower-third", LowerThirdDrop) } )
			{
				var position = Vector3.Zero;
				var angles = Angles.Zero;
				var seen = before;
				for ( var i = 0; i < 8 && !Settled( seen, drop ); i++ )
				{
					var (move, turn) = Step( seen, drop );
					position += move;
					angles += turn;
					rig.Aim( optic, position, angles );
					seen = rig.Measure();
				}

				report.Add( $"{(Settled( seen, drop ) ? "PASS" : "FAIL")} {optic.ResourceName} {label}: Position \"{Format( position )}\" Angles \"{Format( angles )}\": {seen}" );
				report.Add( $"LINE {label} (\"{optic.ResourcePath}\", \"{Format( position )}\", \"{Format( angles )}\")," );
				rig.Save( $"cowitness-{optic.ResourceName}-{label}" );
			}
		}
		catch ( Exception e ) { report.Add( $"FAIL {optic.ResourceName}: {e}" ); }
		finally { scene.Destroy(); }
	}

	/// <summary>
	/// The dot on the screen's centre and the post tip <paramref name="drop"/> (inches) under it, to within 0.006 degrees:
	/// about a pixel of the close-up the dot is found in.
	/// </summary>
	private static bool Settled( Sighting seen, float drop ) =>
		MathF.Abs( seen.DotUp ) < 0.0001f && MathF.Abs( seen.DotLeft ) < 0.0001f
		&& MathF.Abs( seen.TipDrop - drop ) / seen.TipDistance < 0.0001f
		&& MathF.Abs( seen.TipLeft - seen.DotLeft ) < 0.0001f;

	/// <summary>
	/// The next move of the sight line, first order. Moving the eye by (0, y, z) in the gun's frame moves a point r away
	/// by (y, z) / r radians, turning the gun turns everything with it, and the dot is much closer than the post. So the
	/// eye moves to set the dot against the post, <paramref name="drop"/> (inches) over its tip, and the gun turns to put
	/// both on the screen's centre, where the shots go.
	/// </summary>
	private static (Vector3 Move, Angles Turn) Step( Sighting seen, float drop )
	{
		var near = 1f / seen.TipDistance - 1f / seen.DotDistance;
		var z = (-drop / seen.TipDistance - seen.TipUp + seen.DotUp) / near;
		var y = (seen.DotLeft - seen.TipLeft) / near;
		var pitch = seen.DotUp + z / seen.DotDistance;
		var yaw = -seen.DotLeft - y / seen.DotDistance;
		return (new Vector3( 0f, y, z ), new Angles( pitch.RadianToDegree(), yaw.RadianToDegree(), 0f ));
	}

	/// <summary> One of the M16's ManualOffset.OpticSightLines: the optic's resource path, the eye's move and the gun's turn. </summary>
	private sealed class SightLine
	{
		public readonly string Optic;
		public readonly Vector3 Position;
		public readonly Angles Angles;

		public SightLine( string optic, Vector3 position, Angles angles )
		{
			Optic = optic;
			Position = position;
			Angles = angles;
		}
	}

	/// <summary> Where the dot and the post tip show from the aimed eye: up and left of the screen's centre (radians), and how far off (inches). </summary>
	private sealed class Sighting
	{
		public float DotUp, DotLeft, DotDistance, TipUp, TipLeft, TipDistance;
		/// <summary> Degrees between the red drawn and the sight's axis, or null if too little red drew. </summary>
		public float? DotOffTag;
		/// <summary> How far (inches) the post tip is under the dot, at the post: negative is over it. </summary>
		public float TipDrop => (DotUp - TipUp) * TipDistance;

		public override string ToString() =>
			$"dot {DotUp.RadianToDegree():0.000} up {DotLeft.RadianToDegree():0.000} left "
			+ (DotOffTag is { } tag ? $"(red drawn, {tag:0.000} off the sight's axis)" : "(no red drawn: the axis)")
			+ $", post tip {TipDrop:0.000}\" under it, {(TipLeft - DotLeft).RadianToDegree():0.000} left of it, {TipDistance:0.0}\" off";
	}

	/// <summary> The M16's view or world model with its attachment points, in its own scene, with a camera and a light. Build with the scene pushed. </summary>
	private sealed class Rig
	{
		public readonly SkinnedModelRenderer Renderer;
		public readonly GunsmithAttachmentPoint OpticPoint;
		public readonly GunsmithAttachmentPoint BarrelPoint;
		public readonly ulong FactoryBodyGroups;
		private readonly Scene _scene;
		private readonly GameObject _root;
		private readonly CameraComponent _camera;
		private readonly Vector3 _correction;
		/// <summary> ManualOffset.OpticAimAngleCorrection: the gun turned for a 1x sight's collimated dot. </summary>
		private readonly Angles _turn;
		private readonly List<SightLine> _sightLines = new();
		private Model _reticleModel;
		private Vector3 _reticleLocal;

		public Rig( Scene scene, EquipmentResource resource, bool world )
		{
			_scene = scene;
			var gameplay = resource.MainPrefab.Clone( new CloneConfig { StartEnabled = false } );
			var aim = gameplay.GetComponentInChildren<ManualOffset>( true );
			_correction = aim.OpticAimCorrection;
			// By reflection, not through the sight line's type: a tool referencing a type new to the game's code keeps a
			// hotload from loading while the game's old code is still loaded.
			_turn = aim.GetType().GetProperty( "OpticAimAngleCorrection" )?.GetValue( aim ) is Angles turn ? turn : Angles.Zero;
			if ( aim.GetType().GetProperty( "OpticSightLines" )?.GetValue( aim ) is System.Collections.IEnumerable lines )
			{
				foreach ( var line in lines )
				{
					var type = line?.GetType();
					if ( type?.GetProperty( "Optic" )?.GetValue( line ) is not GunsmithPart optic )
						continue;
					var position = type.GetProperty( "Position" )?.GetValue( line ) is Vector3 p ? p : Vector3.Zero;
					var angles = type.GetProperty( "Angles" )?.GetValue( line ) is Angles a ? a : Angles.Zero;
					_sightLines.Add( new SightLine( optic.ResourcePath, position, angles ) );
				}
			}
			gameplay.Destroy();

			_root = (world ? resource.WorldModelPrefab : resource.ViewModelPrefab).Clone( new CloneConfig { StartEnabled = false, Transform = new() } );
			_root.Components.GetOrCreate<GunsmithWeapon>().Resource = resource;
			foreach ( var component in _root.Components.GetAll<Component>( FindMode.EverythingInSelfAndDescendants ) )
				component.Enabled = component is ModelRenderer || component is GunsmithAttachmentPoint;
			Renderer = _root.Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelf );
			Require( Renderer.IsValid() && Renderer.Model is not null && !Renderer.Model.IsError, $"{(world ? "world" : "view")} model compiled" );
			Renderer.UseAnimGraph = false;
			Renderer.PlayAnimationsInEditorScene = true;
			if ( !world ) Renderer.Sequence.Name = "ads";
			Renderer.PlaybackRate = 0;
			var points = _root.Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ).ToArray();
			OpticPoint = points.First( p => p.Category == GunsmithPartType.Optic );
			BarrelPoint = points.First( p => p.Category == GunsmithPartType.Barrel );
			FactoryBodyGroups = Renderer.BodyGroups;
			_root.Enabled = true;
			_scene.EditorTick( .01f, .01f );

			_camera = new GameObject( true, "M16 optic QA camera" ).AddComponent<CameraComponent>();
			_camera.BackgroundColor = new Color( .15f, .22f, .29f );
			_camera.ZNear = .1f;
			_camera.FovAxis = CameraComponent.Axis.Horizontal;
			var light = new GameObject( true, "M16 optic QA light" ).AddComponent<DirectionalLight>();
			light.WorldRotation = Rotation.From( new Angles( 30, -35, 0 ) );
			light.LightColor = Color.White * 2;
			light.SkyColor = Color.White * .8f;
		}

		/// <summary>
		/// Flush the scene's queued starts and removals, pose the gun, then put the parts on it as the game's update does.
		/// Parts fitted since come in on the game's layer too, for the camera.
		/// </summary>
		public void Settle()
		{
			foreach ( var model in _root.Components.GetAll<ModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
			{
				model.RenderOptions.Game = true;
				model.RenderOptions.Overlay = false;
				model.RenderType = ModelRenderer.ShadowRenderType.On;
			}
			_scene.EditorTick( .01f, .01f );
			_scene.EditorTick( .01f, .01f );
			Renderer.SceneModel?.Update( 0 );
			foreach ( var arms in _root.Components.GetAll<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants ) )
				if ( arms != Renderer && arms.SceneModel is not null && Renderer.SceneModel is not null )
					arms.SceneModel.MergeBones( Renderer.SceneModel );
			foreach ( var mount in _root.Components.GetAll<GunsmithMw22Attachment>( FindMode.EverythingInSelfAndDescendants ) )
				mount.RefreshMount();
		}

		/// <summary> The M16's sight line for <paramref name="optic"/> (ManualOffset.OpticSightLines), if it has one. </summary>
		public SightLine SightLineFor( GunsmithPart optic ) =>
			_sightLines.FirstOrDefault( x => string.Equals( x.Optic, optic.ResourcePath, StringComparison.OrdinalIgnoreCase ) );

		/// <summary> How many sight lines the M16's ManualOffset has. </summary>
		public int SightLineCount => _sightLines.Count;

		/// <summary> The aimed eye, in the gun's frame (the gun stays where it was built); see <see cref="Aim"/>. </summary>
		public Vector3 EyePosition { get; private set; }
		public Rotation EyeRotation { get; private set; } = Rotation.Identity;

		/// <summary>
		/// Aim through <paramref name="optic"/> with this sight line, as the game does (ManualOffset, ViewModel.ApplyOffsets):
		/// the view model turned by R, then moved by R * offset in front of the camera. It's the same view with the eye at
		/// -offset, turned by R's inverse, and the gun left where it is: moving the gun again only ever rendered where it
		/// was first put.
		/// </summary>
		public void Aim( GunsmithPart optic, Vector3 linePosition, Angles lineAngles )
		{
			EyeRotation = Rotation.From( optic.OpticAimAngles + (optic.OpticMagnification <= 1f ? _turn : Angles.Zero) + lineAngles ).Inverse;
			EyePosition = -(optic.OpticAimOffset + _correction + linePosition);
		}

		/// <summary> A camera at the eye turned to look at <paramref name="point"/>, keeping the eye's up. </summary>
		public Rotation LookFromEye( Vector3 point ) => Rotation.LookAt( point - EyePosition, EyeRotation.Up );

		public Bitmap Shoot( Vector3 position, Rotation rotation, float fov )
		{
			_camera.WorldPosition = position;
			_camera.WorldRotation = rotation;
			_camera.FieldOfView = fov;
			var bitmap = new Bitmap( Width, Height );
			_camera.RenderToBitmap( bitmap, false );
			return bitmap;
		}

		/// <summary>
		/// The aimed view, 20 degrees wide, with ticks at the edges marking the screen's centre and a short one left of the
		/// post tip's bone, as output/m16-gunsmith/&lt;file&gt;.png.
		/// </summary>
		public void Save( string file )
		{
			using var bitmap = Shoot( EyePosition, EyeRotation, 20f );
			bitmap.SetAntialias( true );
			bitmap.SetPen( Color.Cyan, 2 );
			var tip = ToPixel( PostTipPoint(), EyePosition, EyeRotation, 20f );
			bitmap.DrawLine( new Vector2( tip.x - 70f, tip.y ), new Vector2( tip.x - 40f, tip.y ) );
			bitmap.DrawLine( new Vector2( Width * .5f, 0f ), new Vector2( Width * .5f, 40f ) );
			bitmap.DrawLine( new Vector2( Width * .5f, Height - 40f ), new Vector2( Width * .5f, Height ) );
			bitmap.DrawLine( new Vector2( 0f, Height * .5f ), new Vector2( 40f, Height * .5f ) );
			bitmap.DrawLine( new Vector2( Width - 40f, Height * .5f ), new Vector2( Width, Height * .5f ) );
			File.WriteAllBytes( Path.Combine( Folder, file + ".png" ), bitmap.ToPng() );
		}

		/// <summary> The fitted optic's tag_reticle_attach, in the world, from the MW2022 source's skeleton. </summary>
		public Vector3 ReticleTag()
		{
			var mesh = OpticPoint.CurrentGameObject.Components.Get<ModelRenderer>( FindMode.EverythingInSelf );
			if ( _reticleModel != mesh.Model )
			{
				var key = Path.GetFileNameWithoutExtension( mesh.Model.Name );
				using var doc = System.Text.Json.JsonDocument.Parse( File.ReadAllText( Path.Combine( Project.Current.GetRootPath(), $"Sources/MW2022/models/{key}.json" ) ) );
				var head = doc.RootElement.GetProperty( "bones" ).EnumerateArray()
					.First( b => b.GetProperty( "name" ).GetString() == "tag_reticle_attach" ).GetProperty( "head" );
				_reticleLocal = new Vector3( head[0].GetSingle(), head[1].GetSingle(), head[2].GetSingle() );
				_reticleModel = mesh.Model;
			}
			return mesh.WorldTransform.PointToWorld( _reticleLocal );
		}

		/// <summary>
		/// The fitted optic's forward axis, which its collimated reticle is drawn along (m4_optic_lens.shader): the dot shows
		/// where the sight points, whatever the eye's height.
		/// </summary>
		public Vector3 SightAxis()
		{
			var axis = OpticPoint.CurrentGameObject.Components.Get<ModelRenderer>( FindMode.EverythingInSelf ).WorldRotation.Forward;
			return Vector3.Dot( axis, EyeRotation.Forward ) < 0f ? -axis : axis;
		}

		/// <summary>
		/// Where the dot and the post tip show from the aimed eye. The dot is the red drawn round the sight's axis, close
		/// up, far off (it's collimated), or the axis itself if too little red drew. The tip is <see cref="PostTip"/> on its
		/// bone, which the renders show on the post's tip: the optic can't be hidden to find the post in a render, as the
		/// scene keeps drawing it.
		/// </summary>
		public Sighting Measure()
		{
			var seen = new Sighting();

			var reticle = EyePosition + SightAxis() * 10000f;
			var look = LookFromEye( reticle );
			Vector2? red;
			using ( var bitmap = Shoot( EyePosition, look, ZoomFov ) )
				red = RedCentre( bitmap, ToPixel( reticle, EyePosition, look, ZoomFov ), 250f );
			var toReticle = reticle - EyePosition;
			var dot = red is { } redPixel ? FromPixel( redPixel, look, ZoomFov ) : toReticle.Normal;
			seen.DotOffTag = red.HasValue ? Vector3.GetAngle( dot, toReticle ) : null;
			dot = EyeRotation.Inverse * dot;
			seen.DotUp = MathF.Atan2( dot.z, dot.x );
			seen.DotLeft = MathF.Atan2( dot.y, dot.x );
			seen.DotDistance = toReticle.Length;

			var toTip = PostTipPoint() - EyePosition;
			var tip = EyeRotation.Inverse * toTip.Normal;
			seen.TipUp = MathF.Atan2( tip.z, tip.x );
			seen.TipLeft = MathF.Atan2( tip.y, tip.x );
			seen.TipDistance = toTip.Length;
			return seen;
		}

		/// <summary> The top of the front sight post, in the world. </summary>
		public Vector3 PostTipPoint()
		{
			Require( Renderer.TryGetBoneTransform( "tag_barrel_attach", out var barrel ), "the view model has tag_barrel_attach" );
			return barrel.PointToWorld( PostTip );
		}
	}

	/// <summary> The pixel <paramref name="point"/> shows at, from a camera at <paramref name="position"/>. </summary>
	private static Vector2 ToPixel( Vector3 point, Vector3 position, Rotation rotation, float fov )
	{
		var local = rotation.Inverse * (point - position);
		var focal = Width * .5f / MathF.Tan( (fov * .5f).DegreeToRadian() );
		return new Vector2( Width * .5f - local.y / local.x * focal, Height * .5f - local.z / local.x * focal );
	}

	/// <summary> The direction a camera turned by <paramref name="rotation"/> sees <paramref name="pixel"/> in. </summary>
	private static Vector3 FromPixel( Vector2 pixel, Rotation rotation, float fov )
	{
		var focal = Width * .5f / MathF.Tan( (fov * .5f).DegreeToRadian() );
		return (rotation * new Vector3( focal, Width * .5f - pixel.x, Height * .5f - pixel.y )).Normal;
	}

	/// <summary>
	/// The middle of the red within <paramref name="radius"/> pixels of <paramref name="near"/>, each pixel weighted by
	/// how red it is: the dot, and a ring round it evens out. Null if fewer than 12 pixels are red.
	/// </summary>
	private static Vector2? RedCentre( Bitmap bitmap, Vector2 near, float radius )
	{
		var pixels = bitmap.GetPixels32();
		double x0 = 0, y0 = 0, total = 0;
		var count = 0;
		var top = Math.Max( 0, (int)(near.y - radius) );
		var bottom = Math.Min( bitmap.Height, (int)(near.y + radius) );
		var left = Math.Max( 0, (int)(near.x - radius) );
		var right = Math.Min( bitmap.Width, (int)(near.x + radius) );
		for ( var y = top; y < bottom; y++ )
		{
			for ( var x = left; x < right; x++ )
			{
				var pixel = pixels[y * bitmap.Width + x];
				var red = pixel.r - Math.Max( pixel.g, pixel.b );
				if ( red < 60 )
					continue;

				x0 += (x + .5) * red;
				y0 += (y + .5) * red;
				total += red;
				count++;
			}
		}
		return count < 12 ? null : new Vector2( (float)(x0 / total), (float)(y0 / total) );
	}

	private static string Format( Vector3 value ) => $"{value.x:0.####},{value.y:0.####},{value.z:0.####}";
	private static string Format( Angles value ) => $"{value.pitch:0.####},{value.yaw:0.####},{value.roll:0.####}";

	private static void Require( bool ok, string name )
	{
		if ( !ok ) throw new Exception( "M16 optic QA: " + name );
	}
}
