using Facepunch.UI;
using Sandbox.Audio;
using Sandbox.Rendering;

namespace Facepunch;

/// <summary>
/// How much of a flashbang reached someone, sense by sense. 1 is what reaches you 6 ft (1.83 m) from it, looking
/// straight at it with nothing in the way: where NIJ measured a real one (<see cref="FlashbangGrenade"/>).
/// </summary>
public struct FlashExposure
{
	/// <summary>The light in the eyes.</summary>
	public float Vision;

	/// <summary>The bang in the ears.</summary>
	public float Hearing;

	/// <summary>The blast's jolt to the inner ear.</summary>
	public float Balance;

	/// <summary>Where the flash was on screen (0-1 across and down), if it was in view.</summary>
	public Vector2? Spot;

	/// <summary>How big the flash's image was on screen, in screen widths.</summary>
	public float SpotRadius;

	public readonly bool Any => Vision > 0f || Hearing > 0f || Balance > 0f;
}

/// <summary>
/// What a flashbang does to the player being viewed (<see cref="FlashExposure"/>). Each sense comes back at its own
/// rate: the sight in about 5 s at 6 ft looking straight at it (the M84's figure), the hearing's ringing over 7 s and
/// the balance over 5 s, all sooner the less of it reached them.
/// </summary>
/// <remarks>
/// <para>Sight: flash blindness. Close up, the bleached eyes see nothing but white (<see cref="FlashbangOverlay"/>, over
/// the HUD) for up to a second and a half, then the view comes back through the white: blurred
/// (<c>hc1_flashbang.shader</c>, from the frame's mip chain), glaring (a Bloom and a ChromaticAberration of its own, on
/// a child of the camera, which win over the camera's own), with the frame the flash lit screened over it as an
/// afterimage and the flash's own spot burnt in if it was in view. The sharpness comes back last. With less of its
/// light in the eyes (further off, looking away) the white is fainter and shorter, and there's less blur or none.</para>
/// <para>Hearing: muffled (a DSP on the master mixer) and ringing. Balance: the blast upsets the inner ear, so the view
/// swims (<see cref="RollDegrees"/>), the aim wanders (<see cref="SwayDegrees"/>), the eyes don't focus (more blur) and
/// every gait is slower (<see cref="MoveSpeedScale"/>).</para>
/// </remarks>
public sealed class FlashbangEffect : Component
{
	/// <summary>The ringing in the ears.</summary>
	[Property] public SoundEvent SoundEffect { get; set; }

	/// <summary>Who was flashed.</summary>
	public PlayerPawn Pawn { get; private set; }

	/// <summary>How much slower every gait is at the height of the daze from a blast 6 ft away.</summary>
	private const float MaxSlowdown = 0.3f;

	/// <summary>How far the dazed aim wanders at the daze's height, in degrees.</summary>
	private const float MaxSwayDegrees = 2.5f;

	/// <summary>How far the view rolls to and fro at the daze's height, in degrees: the room seems to tilt.</summary>
	private const float MaxRollDegrees = 4f;

	/// <summary>
	/// From this much light in the eyes up, the white is complete: about 4.5 m away looking straight at it, nearer
	/// looking away.
	/// </summary>
	private const float FullWhite = 0.6f;

	/// <summary>The blur's radius at its worst, as a share of the screen's height.</summary>
	private const float MaxBlur = 0.02f;

	/// <summary>How much of the worst blur the blast's daze gives on its own, at its height.</summary>
	private const float DazeBlur = 0.5f;

	private static FlashbangEffect _current;

	private static Material _material;
	private static Material FlashMaterial => _material ??= Material.FromShader( "shaders/hc1_flashbang.shader" );

	private float _vision;
	private TimeSince _sinceVision;
	private bool _capture;
	private Vector2? _spot;
	private float _spotRadius;

	private float _hearing;
	private TimeSince _sinceHearing;

	private float _balance;
	private TimeSince _sinceBalance;

	private GameObject _layer;
	private Bloom _bloom;
	private ChromaticAberration _aberration;
	private FlashbangOverlay _overlay;

	private CommandList _commands;
	private RenderAttributes _blitAttributes;
	private CameraComponent _camera;
	private Texture _afterimage;
	private Texture _retired;
	private RenderTarget _afterimageTarget;

	private DspProcessor _muffle;
	private SoundHandle _ring;

	/// <summary>
	/// Flashes the player being viewed on this machine, through the scene's camera. A flash that reaches a sense harder
	/// than what's left of the last one starts that sense over.
	/// </summary>
	public static void Apply( PlayerPawn pawn, in FlashExposure exposure, SoundEvent ring )
	{
		var camera = pawn.Scene.Camera;
		if ( !camera.IsValid() )
			return;

		var effect = camera.Components.Get<FlashbangEffect>( FindMode.EverythingInSelf );
		if ( effect.IsValid() && effect.Pawn != pawn )
		{
			effect.Destroy();
			effect = null;
		}

		if ( !effect.IsValid() )
		{
			effect = camera.Components.Create<FlashbangEffect>();
			effect.Flags |= ComponentFlags.NotSaved | ComponentFlags.NotNetworked;
			effect.Pawn = pawn;
		}

		effect.SoundEffect = ring;
		effect.Flash( exposure );
		_current = effect;
	}

	/// <summary>
	/// The share of their speed a flashbang's blast leaves someone: 1 unless they're the one being viewed here and still
	/// dazed. Only the owner moves them, and on their own machine they're the one being viewed.
	/// </summary>
	public static float MoveSpeedScale( PlayerPawn pawn ) => 1f - MaxSlowdown * DazeOf( pawn );

	/// <summary>
	/// How far a flashbang's daze makes their aim wander, in degrees.
	/// </summary>
	public static float SwayDegrees( PlayerPawn pawn ) => MaxSwayDegrees * DazeOf( pawn );

	/// <summary>
	/// How far the view is rolled, in degrees, while the blast's daze lasts: a slow swing to and fro, as the room seems
	/// to tilt. It turns the view about where it looks, so it doesn't move the aim.
	/// </summary>
	public static float RollDegrees( PlayerPawn pawn )
	{
		var effect = _current;
		if ( !effect.IsValid() || effect.Pawn != pawn )
			return 0f;

		var t = (float)effect._sinceBalance;
		return MaxRollDegrees * effect.Daze * (0.7f * MathF.Sin( 2.2f * t ) + 0.3f * MathF.Sin( 4.1f * t + 0.7f ));
	}

	private static float DazeOf( PlayerPawn pawn )
	{
		var effect = _current;
		return effect.IsValid() && effect.Pawn == pawn ? effect.Daze : 0f;
	}

	private void Flash( in FlashExposure exposure )
	{
		if ( exposure.Vision > SightLeft )
		{
			_vision = exposure.Vision;
			_sinceVision = 0f;
			_capture = true;
			_spot = exposure.Spot;
			_spotRadius = exposure.SpotRadius;
		}

		if ( exposure.Hearing > HearingLeft )
		{
			_hearing = exposure.Hearing;
			_sinceHearing = 0f;
			PlayRing();
		}

		if ( exposure.Balance > BalanceLeft )
		{
			_balance = exposure.Balance;
			_sinceBalance = 0f;
		}
	}

	// How long each sense takes to come back. The strengths are already the logarithm of what reached them
	// (FlashbangGrenade), as flash blindness and a deafened ear's recovery grow with the log of the dose, so the times
	// scale with them. Sight: 5 s at 6 ft looking straight at it, the M84's "approximately five seconds". The white lasts
	// 4 s of that, and the sharpness comes back last.

	private static float SightTime( float strength ) => 0.8f + 4.2f * strength;
	private static float WhiteHold( float strength ) => 1.5f * SmoothStep( 0.55f, 1.1f, strength );
	private static float WhiteFade( float strength ) => 0.4f + 2.2f * strength;
	private static float BlurTime( float strength ) => 1f + 5f * strength;
	private static float GlareTime( float strength ) => 1.5f + 4.5f * strength;
	private static float DeafTime( float strength ) => 0.3f + 0.7f * strength;
	private static float MuffleTime( float strength ) => 1.5f + 4f * strength;
	private static float RingTime( float strength ) => 2f + 5f * strength;
	private static float DazeHold( float strength ) => 0.6f * strength;
	private static float DazeTime( float strength ) => 1.5f + 3.5f * strength;

	private float SightLeft => _vision * (1f - Fraction( _sinceVision, SightTime( _vision ) ));
	private float HearingLeft => _hearing * (1f - Fraction( _sinceHearing, RingTime( _hearing ) ));
	private float BalanceLeft => _balance * (1f - Fraction( _sinceBalance, DazeTime( _balance ) ));

	private bool SightOver => _vision <= 0f || _sinceVision >= Math.Max(
		Math.Max( GlareTime( _vision ), BlurTime( _vision ) ),
		Math.Max( WhiteHold( _vision ) + WhiteFade( _vision ), SightTime( _vision ) * (_spot.HasValue ? 2f : 1f) ) );

	private bool HearingOver => _hearing <= 0f || _sinceHearing >= Math.Max( MuffleTime( _hearing ), RingTime( _hearing ) );
	private bool BalanceOver => _balance <= 0f || _sinceBalance >= DazeTime( _balance );

	/// <summary>
	/// The white of flash blindness, 0 to 1: complete from <see cref="FullWhite"/> up, and held for up to 1.5 s when the
	/// flash was that close (1.4 s at 6 ft looking at it), then thinning out as the view comes back through it, over
	/// 2.6 s at 6 ft. Less light gives a fainter white that goes sooner.
	/// </summary>
	private float Veil
	{
		get
		{
			if ( _vision <= 0f )
				return 0f;

			var peak = MathF.Pow( Math.Min( _vision / FullWhite, 1f ), 0.8f );
			var hold = WhiteHold( _vision );
			return peak * (1f - SmoothStep( hold, hold + WhiteFade( _vision ), _sinceVision ));
		}
	}

	/// <summary>
	/// How blurred the view is, 0 to 1. Flash blindness takes the eyes' sharpness, which comes back after the rest of
	/// the sight (none below 0.2 of the light, all of it from 1 up), and the blast's daze stops them focusing.
	/// </summary>
	private float ViewBlur
	{
		get
		{
			var blur = 0f;
			if ( _vision > 0f )
			{
				var clearing = WhiteHold( _vision ) + 0.3f * WhiteFade( _vision );
				blur = SmoothStep( 0.2f, 1f, _vision ) * (1f - SmoothStep( clearing, BlurTime( _vision ), _sinceVision ));
			}

			return Math.Max( blur, DazeBlur * Daze );
		}
	}

	/// <summary>
	/// How strongly the lit frame is screened onto the view.
	/// </summary>
	private float AfterimageAlpha => _vision <= 0f ? 0f
		: 0.55f * MathF.Sqrt( Math.Min( _vision, 1f ) ) * MathF.Pow( 1f - Fraction( _sinceVision, SightTime( _vision ) ), 1.5f );

	/// <summary>
	/// The haze and colour fringes of a dazzled eye. They come up under the white and show as it thins out.
	/// </summary>
	private float Glare => _vision <= 0f ? 0f
		: Math.Min( _vision, 1.2f ) * SmoothStep( 0f, 0.35f, _sinceVision ) * MathF.Pow( 1f - Fraction( _sinceVision, GlareTime( _vision ) ), 1.5f );

	/// <summary>
	/// The flash's own image: bright for the first half of the sight's recovery...
	/// </summary>
	private float SpotBright => _vision <= 0f || !_spot.HasValue ? 0f
		: Math.Min( _vision, 1f ) * Squared( 1f - Fraction( _sinceVision, 0.5f * SightTime( _vision ) ) );

	/// <summary>
	/// ...then a dim blot that fades out over as long again.
	/// </summary>
	private float SpotDark
	{
		get
		{
			if ( _vision <= 0f || !_spot.HasValue )
				return 0f;

			var time = SightTime( _vision );
			return 0.35f * Math.Min( _vision, 1f ) * SmoothStep( 0.2f * time, 0.6f * time, _sinceVision ) * (1f - SmoothStep( time, 2f * time, _sinceVision ));
		}
	}

	/// <summary>
	/// Deaf for a moment, then muffled while it wears off.
	/// </summary>
	private float Muffle => _hearing <= 0f ? 0f
		: Math.Min( _hearing, 1f ) * (1f - SmoothStep( DeafTime( _hearing ), MuffleTime( _hearing ), _sinceHearing ));

	private float RingVolume => _hearing <= 0f ? 0f
		: Math.Min( _hearing, 1f ) * (1f - SmoothStep( 0.35f * RingTime( _hearing ), RingTime( _hearing ), _sinceHearing ));

	/// <summary>
	/// Knocked off balance by the blast (it comes on over a moment rather than jerking the view), unsteady for a while,
	/// then finding their feet again.
	/// </summary>
	private float Daze => _balance <= 0f ? 0f
		: Math.Min( _balance, 1f ) * SmoothStep( 0f, 0.15f, _sinceBalance ) * (1f - SmoothStep( DazeHold( _balance ), DazeTime( _balance ), _sinceBalance ));

	protected override void OnUpdate()
	{
		if ( !Pawn.IsValid() || (SightOver && HearingOver && BalanceOver) )
		{
			Destroy();
			return;
		}

		// The flash's frame is captured before this effect's glare goes on, which would wash it out.
		var capturing = _capture;
		UpdateAfterimage();

		if ( !capturing )
			UpdateGlare();

		UpdateVeil();
		UpdateHearing();
	}

	/// <summary>
	/// A child of the camera for the glare's post-processing and the white's panel, so they all go when it does.
	/// Post-processing on a camera's children comes after its own, so the glare wins over the camera's bloom.
	/// </summary>
	private GameObject Layer
	{
		get
		{
			if ( !_layer.IsValid() )
			{
				_layer = new GameObject( GameObject, true, "Flashbang" );
				_layer.Flags |= GameObjectFlags.NotSaved | GameObjectFlags.NotNetworked;
			}

			return _layer;
		}
	}

	private void UpdateGlare()
	{
		var glare = Glare;
		if ( glare <= 0.005f )
		{
			if ( _bloom.IsValid() ) _bloom.Destroy();
			if ( _aberration.IsValid() ) _aberration.Destroy();
			return;
		}

		if ( !_bloom.IsValid() )
		{
			// The engine takes the mode from the camera's own bloom (additive), so match it.
			_bloom = Layer.Components.Create<Bloom>();
			_bloom.Mode = SceneCamera.BloomAccessor.BloomMode.Additive;
			_bloom.Threshold = 0f;
		}

		if ( !_aberration.IsValid() )
		{
			_aberration = Layer.Components.Create<ChromaticAberration>();
			_aberration.Offset = new Vector3( 6f, 10f, 3f );
		}

		// At threshold 0 the engine's additive bloom adds about Strength / 2 times the blurred view, so this brightens the
		// view up to three times over.
		_bloom.Strength = 4f * glare;
		_aberration.Scale = Math.Min( glare, 1f );
	}

	private void UpdateVeil()
	{
		var veil = Veil;
		if ( veil <= 0.003f )
		{
			if ( _overlay.IsValid() ) _overlay.Destroy();
			return;
		}

		if ( !_overlay.IsValid() )
		{
			// Over the HUD (100), under the map vote (999).
			Layer.Components.GetOrCreate<ScreenPanel>().ZIndex = 200;
			_overlay = Layer.Components.Create<FlashbangOverlay>();
		}

		_overlay.Amount = veil;
	}

	private void UpdateAfterimage()
	{
		// A texture replaced last frame is no longer drawn with.
		_retired?.Dispose();
		_retired = null;

		var alpha = AfterimageAlpha;
		var bright = SpotBright;
		var dark = SpotDark;
		var blur = ViewBlur;
		var blurring = blur > 0.002f;

		var camera = Components.Get<CameraComponent>();
		if ( !camera.IsValid() || (!_capture && alpha <= 0.002f && bright <= 0.002f && dark <= 0.002f && !blurring) )
		{
			ReleaseAfterimage();
			return;
		}

		if ( _capture || _afterimage is null )
		{
			// Half size: it's drawn blurred anyway.
			var size = new Vector2( Math.Max( 1, (int)Screen.Width / 2 ), Math.Max( 1, (int)Screen.Height / 2 ) );
			var texture = Texture.CreateRenderTarget( "hc1_flash_afterimage", ImageFormat.RGBA16161616F, size, _afterimage );
			if ( texture != _afterimage )
			{
				_retired = _afterimage;
				_afterimage = texture;
				_afterimageTarget = RenderTarget.From( texture );
			}

			_capture = true;
		}

		_commands ??= new CommandList( "Flashbang Afterimage" );
		_blitAttributes ??= new RenderAttributes();
		_commands.Reset();

		// The blur reads the frame's mip chain.
		_commands.Attributes.GrabFrameTexture( "ColorBuffer", blurring );

		if ( _capture )
		{
			_commands.Attributes.Set( "FlashMode", 1f );
			_commands.Attributes.Set( "FlashTargetSize", new Vector2( _afterimage.Width, _afterimage.Height ) );
			_commands.SetRenderTarget( _afterimageTarget );
			_commands.Blit( FlashMaterial, _blitAttributes );
			_commands.ClearRenderTarget();
			_capture = false;
		}

		var spot = _spot ?? new Vector2( 0.5f, 0.5f );
		_commands.Attributes.Set( "FlashMode", 0f );
		_commands.Attributes.Set( "FlashAfterimage", _afterimage, -1 );
		_commands.Attributes.Set( "FlashAfterimageTexel", new Vector2( 1f / _afterimage.Width, 1f / _afterimage.Height ) );
		_commands.Attributes.Set( "FlashAfterimageAlpha", alpha );
		_commands.Attributes.Set( "FlashGain", 1f + 3f * Math.Min( _vision, 1f ) );
		_commands.Attributes.Set( "FlashDesaturate", 0.5f );
		_commands.Attributes.Set( "FlashSpot", new Vector4( spot.x, spot.y, _spot.HasValue ? _spotRadius : 0f, Screen.Height / Math.Max( Screen.Width, 1f ) ) );
		_commands.Attributes.Set( "FlashSpotBright", bright );
		_commands.Attributes.Set( "FlashSpotDark", dark );
		_commands.Attributes.Set( "FlashBlur", blurring ? BlurDisc( blur ) : Vector4.Zero );
		_commands.Blit( FlashMaterial, _blitAttributes );

		if ( _camera != camera )
		{
			DetachCommands();
			camera.AddCommandList( _commands, Stage.AfterPostProcess, 10000 );
			_camera = camera;
		}
	}

	/// <summary>
	/// The shader's blur disc: its radius across and down the screen (in its uv), and the mip level each of its taps
	/// reads, about a third of the radius across, so neighbouring taps overlap and together they're smooth.
	/// </summary>
	private static Vector4 BlurDisc( float blur )
	{
		var height = Math.Max( Screen.Height, 1f );
		var radius = MaxBlur * blur * height;
		var level = MathF.Log2( Math.Max( 0.35f * radius, 1f ) );
		return new Vector4( radius / Math.Max( Screen.Width, 1f ), radius / height, level, 0f );
	}

	private void DetachCommands()
	{
		if ( _camera.IsValid() && _commands is not null )
			_camera.RemoveCommandList( _commands );

		_camera = null;
	}

	private void ReleaseAfterimage()
	{
		DetachCommands();
		_commands?.Reset();

		_afterimage?.Dispose();
		_afterimage = null;
		_afterimageTarget = null;
	}

	private void UpdateHearing()
	{
		var muffle = Muffle;
		if ( muffle > 0.005f )
		{
			if ( _muffle is null && Mixer.Master is not null )
			{
				_muffle = new DspProcessor( "weird.4" );
				Mixer.Master.AddProcessor( _muffle );
			}

			if ( _muffle is not null )
				_muffle.Mix = muffle;
		}
		else
		{
			RemoveMuffle();
		}

		if ( _ring.IsValid() )
			_ring.Volume = RingVolume;
	}

	private void PlayRing()
	{
		if ( _ring.IsValid() )
			_ring.Stop( 0.1f );

		_ring = SoundEffect is null ? null : Sound.Play( SoundEffect );
		if ( _ring.IsValid() )
			_ring.Volume = RingVolume;
	}

	private void RemoveMuffle()
	{
		if ( _muffle is null )
			return;

		Mixer.Master?.RemoveProcessor( _muffle );
		_muffle = null;
	}

	protected override void OnDisabled()
	{
		ReleaseAfterimage();
		RemoveMuffle();

		if ( _ring.IsValid() )
			_ring.Volume = 0f;
	}

	protected override void OnDestroy()
	{
		ReleaseAfterimage();
		_retired?.Dispose();
		_retired = null;

		RemoveMuffle();

		if ( _ring.IsValid() )
			_ring.Stop( 0.2f );

		if ( _layer.IsValid() )
			_layer.Destroy();

		if ( _current == this )
			_current = null;
	}

	private static float Fraction( float time, float length ) => length <= 0f ? 1f : Math.Clamp( time / length, 0f, 1f );

	private static float SmoothStep( float from, float to, float x )
	{
		var t = Math.Clamp( (x - from) / (to - from), 0f, 1f );
		return t * t * (3f - 2f * t);
	}

	private static float Squared( float x ) => x * x;
}
