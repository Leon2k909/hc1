using Sandbox.Events;
using Facepunch.Gunsmith;

namespace Facepunch;

/// <summary>
/// A weapon's viewmodel. It's responsibility is to listen to events from a weapon.
/// It should only exist on the client for the currently possessed pawn.
/// </summary>
public partial class ViewModel : WeaponModel, ICameraSetup, IGameEventHandler<PlayerUseEvent>
{
	/// <summary>
	/// A reference to the <see cref="Equipment"/> we want to listen to.
	/// </summary>
	public Equipment Equipment { get; set; }

	/// <summary>
	/// The resource
	/// </summary>
	public EquipmentResource Resource { get; set; }

	/// <summary>
	/// A reference to the viewmodel's arms.
	/// </summary>
	[Property, Group( "Components" )] public SkinnedModelRenderer Arms { get; set; }

	/// <summary>
	/// Is this a throwable?
	/// </summary>
	[Property, Group( "Configuration" )] public bool IsThrowable { get; set; }

	/// <summary>
	/// Looks up the tree to find the player controller.
	/// </summary>
	PlayerPawn Owner => Equipment.IsValid() ? Equipment.Owner : null;

	[Property, Range( 0, 1 ), Group( "Configuration" )] public float IronsightsFireScale { get; set; } = 0.2f;
	[Property, Group( "Configuration" )] public bool UseMovementInertia { get; set; } = true;
	[Property, Range( 0, 1 ), Group( "Configuration" )] public float MoveBobScale { get; set; } = 1f;
	[Property, Range( 0, 2 ), Group( "Configuration" )] public float YawInertiaScale { get; set; } = 2f;

	/// <summary>
	/// Seconds to bring the sights up or down, on viewmodels whose animgraph takes the aim as a weight
	/// (ironsights_weight, Tools/kastov_animgraph.py). The others blend their own ironsights.
	/// </summary>
	[Property, Group( "Configuration" )] public float AimTime { get; set; } = 0.25f;
	private float _aimProgress;

	/// <summary> 0..1, how far the sights are up. It falls back to 0 as the gun comes down after letting go of aim. </summary>
	public float AimProgress => _aimProgress;

	/// <summary>
	/// Fully aimed, with the aim offset's ease finished: the sights are where they'll stay. <see cref="OpticZoom"/> learns
	/// how a magnified optic sits in front of the eye then.
	/// </summary>
	public bool IsAimSettled { get; private set; }

	[Property]
	public float ReloadSpeed { get; set; } = 1f;

	private float PitchInertiaScale => -2f;
	private bool activateInertia = false;
	private float lastPitch;
	private float lastYaw;
	private float YawInertia;
	private float PitchInertia;
	private TimeSince _timeSinceHandMotion = 0f;
	private float _previousHandAimProgress;

	private bool _wasReloading = false;
	private float _lastTimeSinceShoot = 0f;
	private Vector3 sprintPosOffset = Vector3.Zero;
	private Angles sprintAngleOffset = Angles.Zero;

	IEnumerable<IViewModelOffset> Offsets => Equipment.GetComponentsInChildren<IViewModelOffset>();

	/// <summary> Whether a weapon is the SCAR-H, whose viewmodel has its own parameters (deploy, fire, reload) and poses. </summary>
	public static bool IsScarH( EquipmentResource resource ) =>
		resource.IsValid() && resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase );

	/// <summary> The SCAR-H's iron sight aim offset, higher with an optic's mount fitted. </summary>
	public static (Vector3 Position, Angles Angles) ScarHAimOffset( bool hasOptic ) => hasOptic
		? (new Vector3( 0.36f, 2.181f, 0.596f ), new Angles( -1.47f, 0.44f, 0f ))
		: (new Vector3( 0.36f, 2.163f, 0.233f ), new Angles( -0.1f, 0.34f, 0f ));

	/// <summary> The SCAR-H's sprint pose, which its animations don't have. </summary>
	public static readonly Vector3 ScarHSprintPosition = new( 4.29f, -0.86f, -1.1f );
	public static readonly Angles ScarHSprintAngles = new( 8.41f, 59.66f, 0f );

	/// <summary> Where the gun goes while mantling, in the view's space (forward, left, up): back, right and well down. </summary>
	private static readonly Vector3 MantlePosition = new( -3f, -3f, -8f );

	/// <summary> The gun's turn while mantling: muzzle down and a little left, canted right. </summary>
	private static readonly Angles MantleAngles = new( 30f, 10f, 30f );

	/// <summary> Where the gun goes in a slide, in the view's space: a little back, in and down. It doesn't tilt. </summary>
	private static readonly Vector3 SlidePosition = new( -1.5f, 1f, -1.5f );

	void ICameraSetup.Setup( CameraComponent cc )
	{
		if ( !Owner.IsValid() || !Owner.CharacterController.IsValid() )
			return;

		WorldPosition = cc.WorldPosition;
		WorldRotation = cc.WorldRotation;

		// Corner slicing cants the whole gun about the line of sight, so the sights stay on target (ViewModel.CornerSlicing.cs).
		UpdateCornerSlicing( cc );
		WorldRotation *= Rotation.FromRoll( CornerRoll );

		ApplyInertia();
		ApplyOffsets();

		if ( IsThrowable )
		{
			ApplyThrowableAnimations();
		}
		else
		{
			ApplyAnimationParameters();
		}

		ApplyVelocity();
		ApplyAnimationTransform();
		ApplyInspectPose();

		var baseFov = GameSettingsSystem.Current.FieldOfView;

		TargetFieldOfView = TargetFieldOfView.LerpTo( baseFov + FieldOfViewOffset, Time.Delta * 10f );
		FieldOfViewOffset = 0;
	}

	protected override void OnAwake()
	{
		if ( !ModelRenderer.IsValid() )
		{
			ModelRenderer = Components.Get<SkinnedModelRenderer>( FindMode.EverythingInSelfAndDescendants );
		}
		ModelRenderer?.SetBool( "b_deploy_skip", true );
	}

	protected override void OnUpdate()
	{
		UpdateInspect();

		if ( ModelRenderer.IsValid() )
		{
			var (hasOptic, hasMuzzle) = GunsmithAttachmentPoint.BodygroupParts( GameObject );

			if ( !hasMuzzle ) GunsmithAttachmentPoint.ResetFactoryMuzzle( ModelRenderer );

			// Dynamic ADS alignment for SCAR-H based on optic attachment
			if ( Equipment.IsValid() && Equipment.Resource.IsValid() && Equipment.Resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase ) )
			{
				var manualOffset = Equipment.GetComponentInChildren<ManualOffset>();
				if ( manualOffset.IsValid() )
					(manualOffset.AimOffset, manualOffset.AimAngleOffset) = ScarHAimOffset( hasOptic );
			}
		}
	}

	protected override void OnStart()
	{
		// Somehow?
		if ( Owner.IsValid() )
			Owner.OnJump += OnPlayerJumped;

		// Somehow this can happen?
		if ( !Equipment.IsValid() )
			return;

		if ( Equipment.GetComponentInChildren<Shootable>() is { } shoot )
		{
			OnFireMode( shoot.CurrentFireMode );
		}
	}

	void OnPlayerJumped()
	{
		// Keep the sights steady while ADS; the jump pose can rotate the weapon out of alignment.
		if ( Equipment.IsValid() && Equipment.HasTag( "aiming" ) )
			return;

		ModelRenderer?.SetBool( "b_jump", true );
	}

	void ApplyAnimationTransform()
	{
		if ( !ModelRenderer.IsValid() ) return;
		if ( !ModelRenderer.Enabled ) return;
		if ( !Equipment.IsValid() ) return;
		if ( !Equipment.Owner.IsValid() ) return;
		if ( !ModelRenderer.SceneModel.IsValid() ) return;

		var bone = ModelRenderer.SceneModel.GetBoneLocalTransform( "camera" );
		var camera = Equipment.Owner.CameraGameObject;
		if ( !camera.IsValid() ) return;

		var scale = GameSettingsSystem.Current.ViewBob / 100f;

		camera.LocalPosition += bone.Position * scale;
		camera.LocalRotation *= bone.Rotation * scale;
	}

	private Vector3 scopedOffset = 0;
	private Vector3 lerpedPositionOffset;
	private Rotation lerpedRotationOffset;

	void ApplyOffsets()
	{
		var targetPositionOffset = Vector3.Zero;
		var targetRotationOffset = Rotation.Identity;

		// Accumulate all target offsets
		foreach ( var offset in Offsets )
		{
			targetPositionOffset += offset.PositionOffset;
			targetRotationOffset *= offset.AngleOffset.ToRotation();
		}

		// Apply SCAR-H specific procedural sprint and walk bobbing
		if ( Equipment.IsValid() && Equipment.Resource.IsValid() && Equipment.Resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase ) )
		{
			var isAiming = Equipment.HasTag( "aiming" );
			var isSprinting = Owner.IsValid() && Owner.IsSprinting && !isAiming;
			var targetSprintPos = isSprinting ? ScarHSprintPosition : Vector3.Zero;
			var targetSprintAngle = isSprinting ? ScarHSprintAngles : Angles.Zero;

			sprintPosOffset = sprintPosOffset.LerpTo( targetSprintPos, Time.Delta * 10f );
			sprintAngleOffset = Angles.Lerp( sprintAngleOffset, targetSprintAngle, Time.Delta * 10f );

			targetPositionOffset += sprintPosOffset;
			targetRotationOffset *= sprintAngleOffset.ToRotation();

			// Procedural walk/run bobbing
			var moveVel = Owner.CharacterController.Velocity;
			var moveLen = moveVel.Length;
			var isMoving = moveLen > 10f && Owner.IsGrounded && !isSprinting && !Owner.IsSliding;
			
			if ( isMoving )
			{
				var speed = Owner.IsSlowWalking || Owner.IsCrouching ? 8f : 12f;
				var bobTime = RealTime.Now * speed;
				var bobAmount = Owner.IsSlowWalking || Owner.IsCrouching ? 0.1f : 0.25f;
				
				// Simple figure-8 bobbing pattern
				var bobX = MathF.Cos( bobTime ) * bobAmount;
				var bobZ = MathF.Sin( bobTime * 2f ) * bobAmount * 0.5f;
				
				targetPositionOffset += new Vector3( bobX, 0f, bobZ );
				targetRotationOffset *= new Angles( bobZ * 2f, bobX * 2f, bobX * 2f ).ToRotation();
			}
		}

		// Mantling: the support hand goes onto the ledge, so the firing hand swings the gun down and to the right, canted,
		// out of the way (PlayerPawn.Mantle.cs).
		var mantle = Owner.IsValid() ? MathF.Max( Owner.MantleBlend, Owner.PipeClimbBlend ) : 0f;
		if ( mantle > 0f )
		{
			targetPositionOffset += MantlePosition * mantle;
			targetRotationOffset *= (MantleAngles * mantle).ToRotation();
		}

		// Sliding: the gun dips a little as the body drops onto a hip, less as it's aimed, with no tilt (PlayerPawn.Slide.cs).
		var slide = Owner.IsValid() ? Owner.SlideBlend * (1f - _aimProgress) : 0f;
		if ( slide > 0f )
			targetPositionOffset += SlidePosition * slide;

		// Smoothly interpolate position and rotation
		lerpedPositionOffset = lerpedPositionOffset.LerpTo( targetPositionOffset, Time.Delta * 10f );
		lerpedRotationOffset = Rotation.Lerp( lerpedRotationOffset, targetRotationOffset, Time.Delta * 10f );
		IsAimSettled = _aimProgress >= 1f && Equipment.HasTag( "aiming" )
			&& lerpedPositionOffset.Distance( targetPositionOffset ) < 0.01f && lerpedRotationOffset.Distance( targetRotationOffset ) < 0.05f;

		// Apply the lerped offsets
		WorldRotation *= lerpedRotationOffset;
		WorldPosition += WorldRotation * lerpedPositionOffset;

		// Keep existing scoped offset behavior
		scopedOffset = scopedOffset.LerpTo( Owner.HasEquipmentTag( "scoped" ) ? (Vector3.Down * 1.36f + Vector3.Forward * 0.2f) : 0, Time.Delta * 10f );
		LocalPosition += WorldRotation * scopedOffset;
	}

	void ApplyInertia()
	{
		var camera = Equipment.Owner.CameraGameObject;
		var inRot = camera.WorldRotation;

		// Need to fetch data from the camera for the first frame
		if ( !activateInertia )
		{
			lastPitch = inRot.Pitch();
			lastYaw = inRot.Yaw();
			YawInertia = 0;
			PitchInertia = 0;
			activateInertia = true;
		}

		var newPitch = camera.WorldRotation.Pitch();
		var newYaw = camera.WorldRotation.Yaw();

		PitchInertia = Angles.NormalizeAngle( newPitch - lastPitch );
		YawInertia = Angles.NormalizeAngle( lastYaw - newYaw );

		lastPitch = newPitch;
		lastYaw = newYaw;
	}

	private Vector3 lerpedWishMove;

	bool IsLeftFoot = false;
	private float LastStepProgress;
	float lenMult = 0;

	protected void ApplyVelocity()
	{
		if ( !Equipment.IsValid() )
			return;

		var moveVel = Owner.CharacterController.Velocity;
		var moveLen = moveVel.Length;
		var isMoving = moveLen > 10f && !Owner.IsSliding; // Small threshold to determine if actually moving; a slide takes no steps
		var isAiming = Equipment.HasTag( "aiming" );

			var wishMove = Owner.IsWeaponMounted ? Vector3.Zero : Owner.WishMove.Normal * 1f;
		if ( isAiming ) wishMove = 0;

		if ( Owner.IsSlowWalking || Owner.IsCrouching ) moveLen *= 0.5f;

		lerpedWishMove = lerpedWishMove.LerpTo( wishMove, Time.Delta * 7.0f );

		// Missing for a frame or two while a pawn is being replaced (e.g. a forced respawn).
		var footsteps = Owner.GetComponent<PlayerFootsteps>();
		if ( footsteps is null ) return;
		var timeSince = footsteps.TimeSinceStep;
		var freq = footsteps.GetStepFrequency();

		// Set move_bob based on movement
		lenMult = lenMult.LerpTo( isMoving && !isAiming ? moveLen.Remap( 0, 300, 0, 1, true ) : 0, Time.Delta * 10f );
		ModelRenderer?.Set( "move_bob", lenMult * MoveBobScale );

		// Handle cycle when moving vs stopped
		float cycleProgress;

		if ( isMoving && !isAiming )
		{
			// Track step alternation when moving
			if ( timeSince < Time.Delta )
			{
				IsLeftFoot = !IsLeftFoot;
				LastStepProgress = 0f;
			}

			// Calculate progress based on current step (0-0.5 for first step, 0.5-1 for second)
			var stepProgress = (timeSince / freq);
			LastStepProgress = IsLeftFoot
				? stepProgress * 0.5f              // First step: 0 to 0.5
				: 0.5f + (stepProgress * 0.5f);    // Second step: 0.5 to 1

			cycleProgress = LastStepProgress;
		}
		else
		{
			// When stopped, smoothly return to 0
			LastStepProgress = LastStepProgress.LerpTo( 0, Time.Delta * 4.0f );
			cycleProgress = LastStepProgress;
		}

		ModelRenderer?.Set( "move_bob_cycle_control", cycleProgress );

		if ( UseMovementInertia )
			YawInertia += lerpedWishMove.y * 10f;

			var yaw = YawInertia * YawInertiaScale * (Owner.IsWeaponMounted ? 0.3f : 1f) * Owner.TrainingSwayScale;
			var pitch = PitchInertia * PitchInertiaScale * (Owner.IsWeaponMounted ? 0.3f : 1f) * Owner.TrainingSwayScale;
		ModelRenderer?.Set( "aim_yaw_inertia", yaw );
		ModelRenderer?.Set( "aim_pitch_inertia", pitch );

		// The settled ported poses already put each hand on its grip. Re-solving an unchanged pose introduces
		// rapid IK jumps. Blended clips still need IK, as does look/strafe sway while its springs return.
		var reloadable = Equipment.GetComponentInChildren<Reloadable>();
		var shootable = Equipment.GetComponentInChildren<Shootable>();
		var handMotion = MathF.Abs( yaw ) > 0.001f || MathF.Abs( pitch ) > 0.001f
			|| _aimProgress != _previousHandAimProgress || isMoving || Owner.IsSprinting || !Owner.IsGrounded
			|| Equipment.HasTag( "lowered" ) || (reloadable.IsValid() && reloadable.IsReloading)
			|| (shootable.IsValid() && shootable.TimeSinceShoot < 0.25f);
		if ( handMotion ) _timeSinceHandMotion = 0;
		_previousHandAimProgress = _aimProgress;
		ModelRenderer?.Set( "hand_ik_weight", _timeSinceHandMotion < 2f ? 1f : 0f );
	}

	private float FieldOfViewOffset = 0f;
	private float TargetFieldOfView = 90f;

	void ApplyAnimationParameters()
	{
		var aiming = Equipment.HasTag( "aiming" );
		ModelRenderer.SetBool( "b_sprint", Owner.IsSprinting && !aiming );
		// Airborne viewmodel blends can roll the weapon slightly out of the sights.
		// Keep the aimed pose stable until the player leaves ADS.
		ModelRenderer.SetBool( "b_grounded", Owner.IsGrounded || aiming );

		// Ironsights
		ModelRenderer.Set( "ironsights", aiming ? 1 : 0 );
		ModelRenderer.Set( "ironsights_fire_scale", aiming ? IronsightsFireScale : 0f );

		// A weight moving at a steady pace turns back from wherever it is, so letting go of aim halfway in doesn't snap
		// the gun to the sights first (an animgraph selector restarts its blend from the full old pose).
		// The fitted parts' weight slows it (Equipment.AttachmentAimTimeScale).
		var weight = Equipment.AttachmentAimTimeScale > 0f ? Equipment.AttachmentAimTimeScale : 1f;
		weight *= Owner.TrainingAimTimeScale;
		_aimProgress = _aimProgress.Approach( aiming ? 1f : 0f, Time.Delta / MathF.Max( AimTime * weight, 0.01f ) );
		ModelRenderer.Set( "ironsights_weight", _aimProgress * _aimProgress * (3f - 2f * _aimProgress) );

		// The Facepunch guns' graphs (the M4's and the others') bring the sights up by their own clips, at this rate.
		ModelRenderer.Set( "speed_ironsights", 1f / weight );

		var reloadDuration = Equipment.GetComponentInChildren<Reloadable>()?.DurationMultiplier ?? 1f;
		ModelRenderer.Set( "reload_speed", ReloadSpeed / reloadDuration );

		ModelRenderer.SetBool( "b_grab", Owner.Hovered.IsValid() || Owner.IsPipeClimbing );

		ModelRenderer.SetBool( "b_lower_weapon", Equipment.HasTag( "lowered" ) );

		// Handedness
		var holdType = Equipment.GetHoldType();
		ModelRenderer.Set( "holdtype", (int)holdType );
		ModelRenderer.Set( "holdtype_handedness", (int)Equipment.GetHandedness() );
		ModelRenderer.SetBool( "b_twohanded", holdType is AnimationHelper.HoldTypes.Rifle or AnimationHelper.HoldTypes.Shotgun );

		// Weapon state
		ModelRenderer.SetBool( "b_empty", !Equipment.GetComponentInChildren<WeaponAmmo>()?.HasAmmo ?? false );
		// A magazine with its own reload animations (the RPK's box magazines) picks them; 0 is the weapon's own reload.
		ModelRenderer.Set( "reload_variant", Equipment.ReloadMagazine?.ReloadAnimation ?? 0 );

		// Map reload and shooting animations for SCAR-H
		if ( Equipment.IsValid() && Equipment.Resource.IsValid() && Equipment.Resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase ) )
		{
			var reloadable = Equipment.GetComponentInChildren<Reloadable>();
			if ( reloadable.IsValid() )
			{
				if ( reloadable.IsReloading && !_wasReloading )
				{
					var hasAmmo = reloadable.AmmoComponent.IsValid() && reloadable.AmmoComponent.HasAmmo;
					if ( !hasAmmo )
					{
						ModelRenderer?.SetBool( "reload_empty", true );
					}
					else
					{
						ModelRenderer?.SetBool( "reload", true );
					}
				}
				_wasReloading = reloadable.IsReloading;
			}

			var shootable = Equipment.GetComponentInChildren<Shootable>();
			if ( shootable.IsValid() )
			{
				if ( shootable.TimeSinceShoot < _lastTimeSinceShoot )
				{
					if ( aiming )
					{
						ModelRenderer?.SetBool( "fireAimed", true );
					}
					else
					{
						ModelRenderer?.SetBool( "fire", true );
					}
				}
				_lastTimeSinceShoot = shootable.TimeSinceShoot;
			}
		}
	}

	/// <summary>
	/// Should we play deploy effects?
	/// </summary>
	public bool PlayDeployEffects
	{
		set
		{
			ModelRenderer?.SetBool( "b_deploy", value );
			ModelRenderer?.SetBool( "b_deploy_skip", !value );

			// Map to SCAR-H deploy parameter
			if ( Equipment.IsValid() && Equipment.Resource.IsValid() && Equipment.Resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase ) )
			{
				ModelRenderer?.SetBool( "deploy", value );
			}
		}
	}

	private void ApplyThrowableAnimations()
	{
		if ( !Equipment.IsValid() )
			return;

		var throwFn = Equipment.GetComponentInChildren<Throwable>();

		if ( !throwFn.IsValid() )
			return;

		ModelRenderer.SetBool( "b_idle", throwFn.ThrowState == Throwable.State.Idle );
		ModelRenderer.SetBool( "b_pull", throwFn.ThrowState == Throwable.State.Cook );
		ModelRenderer.SetBool( "b_throw", throwFn.ThrowState == Throwable.State.Throwing );
	}

	public void OnFireMode( FireMode currentFireMode )
	{
		var mode = currentFireMode switch
		{
			FireMode.Semi => 1,
			FireMode.Automatic => 3,
			FireMode.Burst => 2,
			_ => 0
		};

		ModelRenderer.Set( "firing_mode", mode );
	}

	void IGameEventHandler<PlayerUseEvent>.OnGameEvent( PlayerUseEvent e )
	{
		ModelRenderer.Set( "grab_action", (int)e.Object.GetGrabAction() );
	}
}
