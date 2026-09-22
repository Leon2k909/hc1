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

	[Property]
	public float ReloadSpeed { get; set; } = 1f;

	private float YawInertiaScale => 2f;
	private float PitchInertiaScale => -2f;
	private bool activateInertia = false;
	private float lastPitch;
	private float lastYaw;
	private float YawInertia;
	private float PitchInertia;

	private bool _wasReloading = false;
	private float _lastTimeSinceShoot = 0f;
	private Vector3 sprintPosOffset = Vector3.Zero;
	private Angles sprintAngleOffset = Angles.Zero;

	IEnumerable<IViewModelOffset> Offsets => Equipment.GetComponentsInChildren<IViewModelOffset>();

	void ICameraSetup.Setup( CameraComponent cc )
	{
		if ( !Owner.IsValid() || !Owner.CharacterController.IsValid() )
			return;

		WorldPosition = cc.WorldPosition;
		WorldRotation = cc.WorldRotation;

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
		ModelRenderer?.Set( "b_deploy_skip", true );
	}

	protected override void OnUpdate()
	{
		UpdateInspect();

		if ( ModelRenderer.IsValid() )
		{
			bool hasOptic = false;
			bool hasMuzzle = false;
			foreach ( var point in Components.GetAll<GunsmithAttachmentPoint>( FindMode.EverythingInSelfAndDescendants ) )
			{
				if ( point.CurrentPart.IsValid() && point.CurrentPart.ModifyBodygroups )
				{
					if ( point.Category == GunsmithPartType.Optic ) hasOptic = true;
					if ( point.Category is GunsmithPartType.Barrel or GunsmithPartType.Muzzle ) hasMuzzle = true;
				}
			}

			if ( !hasMuzzle ) ModelRenderer.SetBodyGroup( "muzzle", 0 );

			// Dynamic ADS alignment for SCAR-H based on optic attachment
			if ( Equipment.IsValid() && Equipment.Resource.IsValid() && Equipment.Resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase ) )
			{
				var manualOffset = Equipment.GetComponentInChildren<ManualOffset>();
				if ( manualOffset.IsValid() )
				{
					if ( hasOptic )
					{
						manualOffset.AimOffset = new Vector3( 0.36f, 2.181f, 0.596f );
						manualOffset.AimAngleOffset = new Angles( -1.47f, 0.44f, 3.9f );
					}
					else
					{
						manualOffset.AimOffset = new Vector3( 0.36f, 2.163f, 0.233f );
						manualOffset.AimAngleOffset = new Angles( -0.1f, 0.34f, 3.9f );
					}
				}
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
		ModelRenderer?.Set( "b_jump", true );
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
			var isSprinting = Owner.IsValid() && Owner.IsSprinting;
			var targetSprintPos = isSprinting ? new Vector3( 4.29f, -0.86f, -1.1f ) : Vector3.Zero;
			var targetSprintAngle = isSprinting ? new Angles( 8.41f, 59.66f, 0f ) : Angles.Zero;

			sprintPosOffset = sprintPosOffset.LerpTo( targetSprintPos, Time.Delta * 10f );
			sprintAngleOffset = Angles.Lerp( sprintAngleOffset, targetSprintAngle, Time.Delta * 10f );

			targetPositionOffset += sprintPosOffset;
			targetRotationOffset *= sprintAngleOffset.ToRotation();

			// Procedural walk/run bobbing
			var moveVel = Owner.CharacterController.Velocity;
			var moveLen = moveVel.Length;
			var isMoving = moveLen > 10f && Owner.IsGrounded && !isSprinting;
			
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

		// Smoothly interpolate position and rotation
		lerpedPositionOffset = lerpedPositionOffset.LerpTo( targetPositionOffset, Time.Delta * 10f );
		lerpedRotationOffset = Rotation.Lerp( lerpedRotationOffset, targetRotationOffset, Time.Delta * 10f );

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
		var isMoving = moveLen > 10f; // Small threshold to determine if actually moving

		var wishMove = Owner.WishMove.Normal * 1f;
		if ( Equipment.HasTag( "aiming" ) ) wishMove = 0;

		if ( Owner.IsSlowWalking || Owner.IsCrouching ) moveLen *= 0.5f;

		lerpedWishMove = lerpedWishMove.LerpTo( wishMove, Time.Delta * 7.0f );

		var footsteps = Owner.GetComponent<PlayerFootsteps>();
		var timeSince = footsteps.TimeSinceStep;
		var freq = footsteps.GetStepFrequency();

		// Set move_bob based on movement
		lenMult = lenMult.LerpTo( isMoving ? moveLen.Remap( 0, 300, 0, 1, true ) : 0, Time.Delta * 10f );
		ModelRenderer?.Set( "move_bob", lenMult );

		// Handle cycle when moving vs stopped
		float cycleProgress;

		if ( isMoving )
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

		ModelRenderer?.Set( "aim_yaw_inertia", YawInertia * YawInertiaScale );
		ModelRenderer?.Set( "aim_pitch_inertia", PitchInertia * PitchInertiaScale );
	}

	private float FieldOfViewOffset = 0f;
	private float TargetFieldOfView = 90f;

	void ApplyAnimationParameters()
	{
		ModelRenderer.Set( "b_sprint", Owner.IsSprinting );
		ModelRenderer.Set( "b_grounded", Owner.IsGrounded );

		var aiming = Equipment.HasTag( "aiming" );
		// Ironsights
		ModelRenderer.Set( "ironsights", aiming ? 1 : 0 );
		ModelRenderer.Set( "ironsights_fire_scale", aiming ? IronsightsFireScale : 0f );

		ModelRenderer.Set( "speed_ironsights", 1 );

		var reloadDuration = Equipment.GetComponentInChildren<Reloadable>()?.DurationMultiplier ?? 1f;
		ModelRenderer.Set( "reload_speed", ReloadSpeed / reloadDuration );

		ModelRenderer.Set( "b_grab", Owner.Hovered.IsValid() );

		ModelRenderer.Set( "b_lower_weapon", Equipment.HasTag( "lowered" ) );

		// Handedness
		var holdType = Equipment.GetHoldType();
		ModelRenderer.Set( "holdtype", (int)holdType );
		ModelRenderer.Set( "holdtype_handedness", (int)Equipment.GetHandedness() );
		ModelRenderer.Set( "b_twohanded", holdType is AnimationHelper.HoldTypes.Rifle or AnimationHelper.HoldTypes.Shotgun );

		// Weapon state
		ModelRenderer.Set( "b_empty", !Equipment.GetComponentInChildren<WeaponAmmo>()?.HasAmmo ?? false );

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
						ModelRenderer?.Set( "reload_empty", true );
					}
					else
					{
						ModelRenderer?.Set( "reload", true );
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
						ModelRenderer?.Set( "fireAimed", true );
					}
					else
					{
						ModelRenderer?.Set( "fire", true );
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
			ModelRenderer?.Set( "b_deploy", value );
			ModelRenderer?.Set( "b_deploy_skip", !value );

			// Map to SCAR-H deploy parameter
			if ( Equipment.IsValid() && Equipment.Resource.IsValid() && Equipment.Resource.ResourceName.Contains( "scarh", StringComparison.OrdinalIgnoreCase ) )
			{
				ModelRenderer?.Set( "deploy", value );
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

		ModelRenderer.Set( "b_idle", throwFn.ThrowState == Throwable.State.Idle );
		ModelRenderer.Set( "b_pull", throwFn.ThrowState == Throwable.State.Cook );
		ModelRenderer.Set( "b_throw", throwFn.ThrowState == Throwable.State.Throwing );
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
