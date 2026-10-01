namespace Facepunch;

/// <summary>
/// A stun grenade. How much of its flash, bang and blast reach the player being viewed depends on the distance, where
/// they're looking, what's in the way and the room it goes off in (<see cref="FlashExposure"/>), and
/// <see cref="FlashbangEffect"/> plays out what that does to them.
/// </summary>
/// <remarks>
/// The figures are NIJ's measurements of a real one, a MK141 Mod 0, at 6, 9 and 12 ft ("Performance Characterization
/// Study: Noise Flash Diversionary Devices", 2003): 27.2, 12.1 and 6.2 million lux, the inverse square law from about 90
/// million candela; 178, 173 and 169 dB, 9 dB less each time the distance doubles; and 0.162, 0.094 and 0.059 bar of
/// overpressure, falling with the distance to the power 1.46. The flash itself lasts 9 ms.
/// </remarks>
[Title( "Flashbang Grenade" )]
public partial class FlashbangGrenade : BaseGrenade, IMarkerObject
{
	/// <summary>
	/// Where is the marker?
	/// </summary>
	Vector3 IMarkerObject.MarkerPosition => WorldPosition;

	/// <summary>
	/// How far can we see this marker?
	/// </summary>
	float IMarkerObject.MarkerMaxDistance => 512f;

	/// <summary>
	/// What icon?
	/// </summary>
	string IMarkerObject.MarkerIcon => "/ui/weapons/grenades/he_grenade_01.png";

	/// <summary>
	/// What text?
	/// </summary>
	string IMarkerObject.DisplayText => "Flashbang";

	/// <summary>
	/// The ringing in the ears while the hearing comes back.
	/// </summary>
	[Property]
	public SoundEvent SoundEffect { get; set; }

	/// <summary>
	/// The sound effect to use when the flashbang explodes.
	/// </summary>
	[Property]
	public SoundEvent ExplodeSound { get; set; }

	/// <summary>6 ft (1.83 m), the nearest NIJ measured at. Each sense's strength is 1 there.</summary>
	private const float ReferenceDistance = 72f;

	/// <summary>The flash comes from the grenade's middle, not its origin.</summary>
	private const float FlashHeight = 6f;

	/// <summary>Further than 19 m none of it reaches anyone: the sight's effect ends first, at about 18 m.</summary>
	private const float MaxReach = 750f;

	/// <summary>More than this gains nothing, however close you are.</summary>
	private const float MaxStrength = 1.3f;

	/// <summary>cos 100 degrees: how far out from where the eyes look they still take in light.</summary>
	private const float EdgeOfView = -0.1736f;

	/// <summary>
	/// How many tenfold cuts in the light take the sight's effect from full to nothing: 2, which is 100 times less light
	/// than at 6 ft, or looking straight at it from about 18 m. That's still ~2,400 lux-seconds in the eyes, what a
	/// full-power camera flash (guide number 60) gives from 2 m, which leaves an afterimage for a few seconds.
	/// </summary>
	private const float SightDecades = 2f;

	/// <summary>The fireball's radius, for the spot its image burns into the eyes.</summary>
	private const float FireballRadius = 12f;

	/// <summary>How far the rays that find the walls, floor and ceiling the flash lights go.</summary>
	private const float BounceReach = 600f;

	/// <summary>A room's average reflectance: pale walls 0.5-0.8, darker floors 0.2-0.3.</summary>
	private const float Reflectance = 0.4f;

	/// <summary>
	/// How much a lit room bleaches the eyes compared with the same light straight from the flash, which the eye focuses
	/// onto a small patch of the retina.
	/// </summary>
	private const float BounceShare = 0.25f;

	/// <summary>dB at 6 ft.</summary>
	private const float ReferenceLevel = 178f;

	private const float LevelPerDoubling = 9f;

	/// <summary>
	/// Where the ringing starts: above a rifle shot at the shooter's ear (155-165 dB), which rings nobody's ears here.
	/// That's about 7 m away in the open.
	/// </summary>
	private const float RingLevel = 160f;

	/// <summary>What a wall or a corner takes off the bang, which gets round them far better than light.</summary>
	private const float WallLoss = 12f;

	/// <summary>Bar at 6 ft.</summary>
	private const float ReferencePressure = 0.162f;

	private const float PressureFalloff = 1.46f;

	/// <summary>Where the blast stops unsteadying you: 0.035 bar (0.5 psi), about 5 m away in the open.</summary>
	private const float DazePressure = 0.035f;

	/// <summary>How much of the blast gets round a wall or a corner.</summary>
	private const float WallPressure = 0.5f;

	protected override void Explode()
	{
		base.Explode();

		// The flash is seen at once, the bang heard when it gets there.
		if ( ExplodeSound is not null )
			GunshotAudio.PlayDelayed( ExplodeSound, WorldPosition, GunshotAudio.SoundDelay( WorldPosition ) );

		var viewer = Client.Viewer?.PlayerPawn;
		if ( !viewer.IsValid() || viewer.HealthComponent.State != LifeState.Alive )
			return;

		var exposure = Measure( viewer );
		if ( exposure.Any )
			FlashbangEffect.Apply( viewer, exposure, SoundEffect );
	}

	private FlashExposure Measure( PlayerPawn viewer )
	{
		var flash = WorldPosition + Vector3.Up * FlashHeight;
		var eye = viewer.Head.IsValid() ? viewer.Head.WorldPosition : viewer.EyePosition;
		var distance = Math.Max( flash.Distance( eye ), 12f );
		if ( distance > MaxReach )
			return default;

		var ratio = distance / ReferenceDistance;

		// Light gets through a window. The bang and the blast mostly don't.
		var lightReaches = IsClear( flash, eye, viewer, true );
		var soundReaches = lightReaches && IsClear( flash, eye, viewer, false );

		var look = viewer.EyeAngles.ToRotation().Forward;
		var direct = lightReaches ? Facing( look.Dot( (flash - eye).Normal ) ) / (ratio * ratio) : 0f;
		var light = direct + Bounced( flash, eye, look, viewer );

		var level = ReferenceLevel - LevelPerDoubling * MathF.Log2( ratio ) - (soundReaches ? 0f : WallLoss);
		var pressure = ReferencePressure * MathF.Pow( ratio, -PressureFalloff ) * (soundReaches ? 1f : WallPressure);

		var exposure = new FlashExposure
		{
			// Flash blindness lasts longer the more light reached the eyes, by its logarithm.
			Vision = light > 0f ? Strength( 1f + MathF.Log10( light ) / SightDecades ) : 0f,
			Hearing = Strength( (level - RingLevel) / (ReferenceLevel - RingLevel) ),
			Balance = Strength( MathF.Log( pressure / DazePressure ) / MathF.Log( ReferencePressure / DazePressure ) ),
		};

		if ( direct > 0f && exposure.Vision > 0f )
			FindSpot( flash, ref exposure );

		return exposure;
	}

	private static float Strength( float x ) => Math.Clamp( x, 0f, MaxStrength );

	/// <summary>
	/// How much of the flash's light the eyes take in, by how far from where they're looking it is: all of it straight
	/// ahead, less towards the edge of the field of view, and none past it, 100 degrees out.
	/// </summary>
	private static float Facing( float cos ) => MathF.Pow( Math.Max( 0f, (cos - EdgeOfView) / (1f - EdgeOfView) ), 1.5f );

	/// <summary>
	/// The light the flash throws on the walls, floor and ceiling round it that reaches the viewer's eyes, from 18 rays
	/// (the 6 axes and the 12 diagonals between them). Each lit patch counts by how squarely its lit side faces the
	/// viewer, how near the middle of their view it is and how close it is to them. How far it is from the flash doesn't
	/// matter: a further patch is dimmer but bigger. Light that bounces again adds 1 / (1 - reflectance x the share of
	/// rays that hit something). Indoors, this is what dazzles you when you look away. In the open, little comes back.
	/// </summary>
	private float Bounced( Vector3 flash, Vector3 eye, Vector3 look, PlayerPawn viewer )
	{
		var seen = 0f;
		var hits = 0;

		for ( var x = -1; x <= 1; x++ )
		{
			for ( var y = -1; y <= 1; y++ )
			{
				for ( var z = -1; z <= 1; z++ )
				{
					var axes = Math.Abs( x ) + Math.Abs( y ) + Math.Abs( z );
					if ( axes is 0 or 3 )
						continue;

					var ray = Solid( Scene.Trace.Ray( flash, flash + new Vector3( x, y, z ).Normal * BounceReach ) )
						.WithoutTags( BreakableGlass.Tag )
						.IgnoreGameObjectHierarchy( GameObject.Root )
						.Run();

					if ( !ray.Hit )
						continue;

					hits++;

					var patch = ray.EndPosition + ray.Normal * 2f;
					var range = patch.Distance( eye );
					if ( range < 1f )
						continue;

					var towards = (patch - eye) / range;
					var inView = look.Dot( towards );
					var litSide = -ray.Normal.Dot( towards );
					if ( inView <= 0f || litSide <= 0f || !IsClear( eye, patch, viewer, true ) )
						continue;

					var near = Math.Max( range, 24f ) / ReferenceDistance;
					seen += inView * litSide / (near * near);
				}
			}
		}

		return BounceShare * 4f * Reflectance / 18f * seen / (1f - Reflectance * hits / 18f);
	}

	/// <summary>
	/// Is there nothing solid between these points?
	/// </summary>
	private bool IsClear( Vector3 from, Vector3 to, PlayerPawn viewer, bool throughGlass )
	{
		var trace = Solid( Scene.Trace.Ray( from, to ) )
			.IgnoreGameObjectHierarchy( GameObject.Root )
			.IgnoreGameObjectHierarchy( viewer.GameObject.Root );

		if ( throughGlass )
			trace = trace.WithoutTags( BreakableGlass.Tag );

		return !trace.Run().Hit;
	}

	/// <summary>
	/// Walls and props only: people, bodies, player clips and other grenades don't block it. A trace keeps at most 8
	/// tags to leave out and drops any more, so this leaves room for one: glass.
	/// </summary>
	private static SceneTrace Solid( SceneTrace trace ) =>
		trace.WithoutTags( "trigger", "playerclip", "movement", "player", "ragdoll", "enemy", "grenade" );

	/// <summary>
	/// Where the flash's image burns into the eyes, if it was on screen: the fireball's own size, bigger the nearer it
	/// is, spread a little by the glare round it.
	/// </summary>
	private void FindSpot( Vector3 flash, ref FlashExposure exposure )
	{
		var camera = Scene.Camera;
		if ( !camera.IsValid() )
			return;

		var centre = camera.PointToScreenNormal( flash, out var behind );
		if ( behind || centre.x < 0f || centre.x > 1f || centre.y < 0f || centre.y > 1f )
			return;

		var edge = camera.PointToScreenNormal( flash + camera.WorldRotation.Right * FireballRadius, out _ );
		exposure.Spot = centre;
		exposure.SpotRadius = Math.Max( Math.Abs( edge.x - centre.x ) * 1.3f, 0.01f );
	}
}
