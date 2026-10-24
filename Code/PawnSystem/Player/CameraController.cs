using Sandbox.Events;

namespace Facepunch;

public enum CameraMode
{
	FirstPerson,
	ThirdPerson
}

public interface ICameraSetup : ISceneEvent<ICameraSetup>
{
	// Effects before viewmodel
	public void PreSetup( CameraComponent cc ) { }

	// Place viewmodel
	public void Setup( CameraComponent cc ) { }

	// Effects including viewmodel
	public void PostSetup( CameraComponent cc ) { }

	// Follows the viewmodel's final pose, after PostSetup's arm posers
	public void LateSetup( CameraComponent cc ) { }
}

public sealed partial class CameraController : PawnCameraController, IGameEventHandler<DamageTakenEvent>
{
	[Property] public PlayerPawn Player { get; set; }

	[Property, Group( "Config" )] public bool ShouldViewBob { get; set; } = true;

	[Property] public float ThirdPersonDistance { get; set; } = 64f;
	[Property] public float AimFovOffset { get; set; } = -5f;

	private CameraMode _mode;
	public CameraMode Mode
	{
		get => _mode;
		set
		{
			if ( _mode == value )
				return;

			_mode = value;
			OnModeChanged();
		}
	}

	public float MaxBoomLength { get; set; }

	private float FieldOfViewOffset = 0f;
	private float TargetFieldOfView = 90f;

	/// <summary>
	/// Constructs a ray using the camera's GameObject
	/// </summary>
	public Ray AimRay
	{
		get
		{
			if ( Camera.IsValid() )
			{
				return new( Camera.WorldPosition + Camera.WorldRotation.Forward, Camera.WorldRotation.Forward );
			}

			return new( WorldPosition + Vector3.Up * 64f, Player.EyeAngles.ToRotation().Forward );
		}
	}

	public void AddFieldOfViewOffset( float degrees )
	{
		FieldOfViewOffset -= degrees;
	}

	private void UpdateRotation()
	{
		Boom.WorldRotation = Player.EyeAngles.ToRotation();
	}

	public override void SetActive( bool isActive )
	{
		base.SetActive( isActive );
		OnModeChanged();
		Boom.WorldRotation = Player.EyeAngles.ToRotation();
	}

	protected override void OnPreRender()
	{
		UpdateMouseVisibility();

		if ( !Camera.IsValid() )
			return;

		ICameraSetup.Post( x => x.PreSetup( Camera ) );
		ICameraSetup.Post( x => x.Setup( Camera ) );
		ICameraSetup.Post( x => x.PostSetup( Camera ) );
		ICameraSetup.Post( x => x.LateSetup( Camera ) );

		UpdateMouseVisibility();
	}

	/// <summary>
	/// Updates the camera's position, from player code
	/// </summary>
	/// <param name="eyeHeight"></param>
	internal void UpdateFromEyes( float eyeHeight )
	{
		if ( !Camera.IsValid() )
			return;

		// All transform effects are additive to camera local position, so we need to reset it before anything is applied
		Camera.LocalPosition = Vector3.Zero;
		Camera.LocalRotation = Rotation.Identity;

		if ( Mode == CameraMode.ThirdPerson && !Player.IsLocallyControlled )
		{
			// orbit cam: spectating only
			var angles = Boom.WorldRotation.Angles();
			angles += Input.AnalogLook;
			Boom.WorldRotation = angles.WithPitch( angles.pitch.Clamp( -90, 90 ) ).ToRotation();
		}
		else
		{
			UpdateRotation();
		}

		if ( MaxBoomLength > 0 )
		{
			var traceStart = Boom.WorldPosition;
			var traceEnd = Boom.WorldRotation.Backward * MaxBoomLength;

			// Right amount for third person
			traceEnd += Boom.WorldRotation.Right * 25f;

			var tr = Scene.Trace.Ray( traceStart, traceStart + traceEnd )
				.IgnoreGameObjectHierarchy( GameObject.Root )
				.WithoutTags( "trigger", "player", "ragdoll" )
				.Run();

			Camera.WorldPosition = tr.EndPosition;
		}

		if ( ShouldViewBob )
		{
			ViewBob();
		}

		ApplyAimBreathing();
		Update( eyeHeight );
	}

	float walkBob = 0;
	private float LerpBobSpeed = 0;

	[DeveloperCommand( "Toggle Third Person", "Player" )]
	public static void ToggleThirdPerson()
	{
		var pl = Client.Local.PlayerPawn;
		pl.CameraController.Mode = pl.CameraController.Mode == CameraMode.FirstPerson ? CameraMode.ThirdPerson : CameraMode.FirstPerson;
	}

	/// <summary>
	/// Bob the view!
	/// This could be better, but it doesn't matter really.
	/// </summary>
	void ViewBob()
	{
		if ( Mode != CameraMode.FirstPerson )
			return;

		var bobSpeed = Player.CharacterController.Velocity.Length.LerpInverse( 0, 300 );
		if ( !Player.IsGrounded ) bobSpeed *= 0.1f;
		if ( !Player.IsSprinting ) bobSpeed *= 0.3f;

		LerpBobSpeed = LerpBobSpeed.LerpTo( bobSpeed, Time.Delta * 10f );

		walkBob += Time.Delta * 10.0f * LerpBobSpeed;
		var yaw = MathF.Sin( walkBob ) * 0.5f;
		var pitch = MathF.Cos( -walkBob * 2f ) * 0.5f;

		Boom.LocalRotation *= Rotation.FromYaw( -yaw * LerpBobSpeed );
		Boom.LocalRotation *= Rotation.FromPitch( -pitch * LerpBobSpeed * 0.5f );
	}

	private void ApplyScope()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.CurrentEquipment.IsValid() )
			return;

		// The scope zooms the aimed view further, so it follows the ADS Field Of View setting too.
		if ( Player.CurrentEquipment.GetComponentInChildren<FlatScope>() is { } scope )
		{
			var aimed = HipFieldOfView + FieldOfViewOffset;
			FieldOfViewOffset += Equipment.ZoomFov( aimed, scope.GetMagnification() ) - aimed;
		}
	}

	/// <summary>
	/// The field of view before aiming and effects: Settings → Video's Field Of View in first person, its Third Person
	/// Field Of View from behind (the deathcam, spectating).
	/// </summary>
	public float HipFieldOfView => Mode == CameraMode.ThirdPerson
		? GameSettingsSystem.Current.ThirdPersonFieldOfView
		: GameSettingsSystem.Current.FieldOfView;

	OpticZoom opticZoom;

	private void Update( float eyeHeight )
	{
		var baseFov = HipFieldOfView;
		FieldOfViewOffset = 0;

		if ( !Player.IsValid() )
			return;

		if ( Player.IsLocallyControlled && !opticZoom.IsValid() )
		{
			opticZoom = Components.GetOrCreate<OpticZoom>( FindMode.EverythingInSelf );
			opticZoom.Flags |= ComponentFlags.NotSaved | ComponentFlags.NotNetworked;
			opticZoom.CameraController = this;
		}

		if ( Player.CurrentEquipment.IsValid() )
		{
			if ( Player.CurrentEquipment.HasTag( "aiming" ) )
			{
				FieldOfViewOffset += Player.CurrentEquipment.GetAimFovOffset( baseFov );
			}
		}

		// deathcam, "zoom" at target.
		if ( Player.HealthComponent.State == LifeState.Dead )
		{
			FieldOfViewOffset += AimFovOffset;
		}

		ApplyRecoil();
		ApplyWoundSway();
		ApplyFlashSway();
		ApplyScope();

		Boom.LocalPosition = Vector3.Zero.WithZ( eyeHeight );

		ApplyCameraEffects();
		ScreenShaker?.Apply( Camera );
		ApplyFlashRoll();
		ApplyMantleTilt();
		UpdateMouseVisibility();

		TargetFieldOfView = TargetFieldOfView.LerpTo( baseFov + FieldOfViewOffset, Time.Delta * 5f );
		Camera.FieldOfView = TargetFieldOfView;
		opticZoom?.UpdateCamera( baseFov );
	}

	private void UpdateMouseVisibility()
	{
		if ( !Player.IsValid() )
			return;

		if ( !IsActive && !GameUtils.IsActiveCombatPlayer( Player ) )
			return;

		GameUtils.TraceCombatMouse( "CameraController.UpdateMouseVisibility.before", Player );
		GameUtils.UpdateCombatMouseVisibility( Player );
		GameUtils.TraceCombatMouse( "CameraController.UpdateMouseVisibility.after", Player );
	}

	protected override void OnDisabled()
	{
		base.OnDisabled();
		UpdateMouseVisibilityOnDetach();
	}

	protected override void OnDestroy()
	{
		base.OnDestroy();
		UpdateMouseVisibilityOnDetach();
	}

	private void UpdateMouseVisibilityOnDetach()
	{
		if ( GameMode.Instance.IsValid() )
			GameUtils.UpdateCombatMouseVisibility( GameUtils.IsActiveCombatPlayer( Player ) ? Player : null );
		else
			Mouse.Visibility = MouseVisibility.Auto;
	}

	RealTimeSince TimeSinceDamageTaken = 1;

	void IGameEventHandler<DamageTakenEvent>.OnGameEvent( DamageTakenEvent eventArgs )
	{
		TimeSinceDamageTaken = 0;
	}


	float depthOfFieldScale = 0f;
	void ApplyCameraEffects()
	{
		var timeSinceDamage = TimeSinceDamageTaken.Relative;
		var shortDamageUi = timeSinceDamage.LerpInverse( 0.1f, 0.0f, true );
		ChromaticAberration.Scale = shortDamageUi * 1f;
		Pixelate.Scale = shortDamageUi * 0.2f;

		if ( Player.HasEquipmentTag( "scoped" ) )
		{
			depthOfFieldScale = depthOfFieldScale.LerpTo( 1, Time.Delta * 3f );
			DepthOfField.Enabled = true;
			DepthOfField.BlurSize = depthOfFieldScale.Remap( 0, 1, 0, 25 );
		}
		else
		{
			depthOfFieldScale = depthOfFieldScale.LerpTo( 0, Time.Delta * 15f );
			DepthOfField.BlurSize = depthOfFieldScale.Remap( 0, 1, 0, 25 );

			if ( depthOfFieldScale.AlmostEqual( 0, 0.1f ) )
				DepthOfField.Enabled = false;
		}
	}

	void ApplyRecoil()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.CurrentEquipment.IsValid() )
			return;

		if ( Player.CurrentEquipment.GetComponentInChildren<ShootRecoil>() is { } fn )
			Player.EyeAngles += fn.Current;
	}

	/// <summary>How far the aim wanders per arm wound (up to two count), in degrees, standing.</summary>
	private const float WoundSwayDegrees = 0.35f;
	private Angles _woundSway;

	/// <summary>
	/// Hardcore: a shot arm or hand can't hold the gun still (<see cref="HealthComponent.ArmWounds"/>). The aim wanders
	/// slowly around where you point it, with a slight tremor, less when braced crouching or prone, and you have to keep
	/// correcting it. The shots go where the sights are.
	/// </summary>
	void ApplyWoundSway()
	{
		var health = Player.HealthComponent;
		var wounds = Player.IsLocallyControlled && health.State == LifeState.Alive ? Math.Min( health.ArmWounds, 2 ) : 0;
		var amplitude = WoundSwayDegrees * wounds * (Player.IsProne ? 0.4f : Player.IsCrouching ? 0.7f : 1f);

		// Sines that never line up, so the drift doesn't visibly repeat.
		var t = Time.Now;
		var sway = new Angles(
			MathF.Sin( t * 1.1f ) * 0.55f + MathF.Sin( t * 2.3f + 1.7f ) * 0.35f + MathF.Sin( t * 6.7f + 0.3f ) * 0.1f,
			MathF.Sin( t * 0.9f + 0.6f ) * 0.55f + MathF.Sin( t * 1.9f + 2.9f ) * 0.35f + MathF.Sin( t * 7.9f ) * 0.1f,
			0f ) * amplitude;

		Player.EyeAngles += sway - _woundSway;
		_woundSway = sway;
	}

	private Angles _flashSway;

	/// <summary>
	/// A flashbang's blast upsets the balance, so the aim wanders while it wears off (<see cref="FlashbangEffect"/>):
	/// quicker and shakier than a wounded arm's drift, and gone in a few seconds.
	/// </summary>
	void ApplyFlashSway()
	{
		var amplitude = Player.IsLocallyControlled ? FlashbangEffect.SwayDegrees( Player ) : 0f;

		var t = Time.Now;
		var sway = new Angles(
			MathF.Sin( t * 2.1f ) * 0.5f + MathF.Sin( t * 3.7f + 1.1f ) * 0.35f + MathF.Sin( t * 8.3f + 0.4f ) * 0.15f,
			MathF.Sin( t * 1.7f + 0.8f ) * 0.5f + MathF.Sin( t * 3.1f + 2.3f ) * 0.35f + MathF.Sin( t * 7.3f ) * 0.15f,
			0f ) * amplitude;

		Player.EyeAngles += sway - _flashSway;
		_flashSway = sway;
	}

	/// <summary>
	/// A flashbang's blast upsets the inner ear, so the room seems to tilt to and fro while it wears off
	/// (<see cref="FlashbangEffect.RollDegrees"/>). Only the camera rolls, about where it looks, so the aim stays put.
	/// </summary>
	void ApplyFlashRoll()
	{
		var roll = FlashbangEffect.RollDegrees( Player );
		if ( roll != 0f )
			Camera.LocalRotation *= Rotation.FromRoll( roll );
	}

	/// <summary>
	/// Going over a ledge the head comes forward and down, leaning a little to the support hand on the ledge
	/// (<see cref="PlayerPawn.MantleBlend"/>). Only the camera turns, and you can't shoot meanwhile.
	/// </summary>
	void ApplyMantleTilt()
	{
		if ( Mode != CameraMode.FirstPerson )
			return;

		var blend = Player.MantleBlend;
		if ( blend > 0f )
			Camera.LocalRotation *= Rotation.From( 6f * blend, 0f, -3f * blend );
	}

	void OnModeChanged()
	{
		SetBoomLength( Mode == CameraMode.FirstPerson ? 0.0f : ThirdPersonDistance );

		if ( Camera.IsValid() )
		{
			// Update render exclude tags
			Camera.RenderExcludeTags.Set( "viewer", Mode == CameraMode.FirstPerson );
		}

		var firstPersonPOV = Mode == CameraMode.FirstPerson && IsActive;

		if ( Player.IsValid() && Player.Body.IsValid() )
		{
			Player.Body.SetFirstPersonView( firstPersonPOV );
		}

		if ( firstPersonPOV )
			Player.CreateViewModel( false );
		else
			Player.ClearViewModel();
	}

	private void SetBoomLength( float length )
	{
		MaxBoomLength = length;
	}
}
