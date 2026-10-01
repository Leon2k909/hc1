using Sandbox.Events;

namespace Facepunch;

public partial class PlayerPawn : IGameEventHandler<WeaponShotEvent>
{
	/// <summary>
	/// Called when the player jumps.
	/// </summary>
	[Property] public Action OnJump { get; set; }

	/// <summary>
	/// The player's box collider, so people can jump on other people.
	/// </summary>
	[Property] public BoxCollider PlayerBoxCollider { get; set; }

	[RequireComponent] public TagBinder TagBinder { get; set; }

	/// <summary>
	/// How tall are we?
	/// </summary>
	[Property, Group( "Config" )] public float Height { get; set; } = 64f;

	[Property, Group( "Fall Damage" )] public float MinimumFallVelocity { get; set; } = 500f;
	[Property, Group( "Fall Damage" )] public float MinimumFallSoundVelocity { get; set; } = 300f;
	[Property, Group( "Fall Damage" )] public float FallDamageScale { get; set; } = 0.2f;
	[Property, Group( "Fall Damage" )] public float FallKnockdownVelocity { get; set; } = 650f;
	[Property, Group( "Fall Damage" )] public float FallKnockdownDuration { get; set; } = 1.25f;

	[Property, Group( "Sprint" )] public float SprintMovementDampening { get; set; } = 0.35f;

	/// <summary>
	/// Noclip movement speed
	/// </summary>
	[Property] public float NoclipSpeed { get; set; } = 1000f;

	public PlayerGlobals Global => GetGlobal<PlayerGlobals>();

	/// <summary>
	/// Look direction of this player. Smoothly interpolated for networked players.
	/// </summary>
	public override Angles EyeAngles
	{
		get => _smoothEyeAngles;
		set
		{
			if ( !IsProxy ) _smoothEyeAngles = value;
			_rawEyeAngles = value;
		}
	}
	[Sync] private Angles _rawEyeAngles { get; set; }
	private Angles _smoothEyeAngles;

	/// <summary>
	/// Is the player crouching?
	/// </summary>
	[Sync] public bool IsCrouching { get; set; }

	/// <summary>
	/// Are we lying down? Toggled with the Prone action rather than held, since you shouldn't have to
	/// keep a key down to stay on the floor.
	/// </summary>
	[Sync] public bool IsProne { get; set; }

	/// <summary>Downed in Zombies last update, so a revive stands them up.</summary>
	private bool _wasDowned;
	[Sync] private bool IsFallKnockedDown { get; set; }
	[Sync] private TimeSince TimeSinceFallKnockdown { get; set; }

	/// <summary>
	/// Is the player slow walking?
	/// </summary>
	[Sync] public bool IsSlowWalking { get; set; }

	/// <summary>
	/// Are we sprinting?
	/// </summary>
	[Sync] public bool IsSprinting { get; set; }

	/// <summary>
	/// Is the player noclipping?
	/// </summary>
	[Sync] public bool IsNoclipping { get; set; }

	/// <summary>
	/// If true, we're not allowed to move.
	/// </summary>
	[Sync( SyncFlags.FromHost )] public bool IsFrozen { get; set; }

	/// <summary>
	/// Last time this player moved or attacked.
	/// </summary>
	[Sync] public TimeSince TimeSinceLastInput { get; private set; }

	/// <summary>
	/// What's our holdtype?
	/// </summary>
	[Sync] AnimationHelper.HoldTypes CurrentHoldType { get; set; } = AnimationHelper.HoldTypes.None;

	/// <summary>
	/// Synced velocity for animation replication to remote players
	/// </summary>
	[Sync] public Vector3 SyncedVelocity { get; set; }

	/// <summary>
	/// Synced ground state for animation replication to remote players
	/// </summary>
	[Sync] public bool SyncedIsGrounded { get; set; }

	/// <summary>
	/// How quick do we wish to go?
	/// </summary>
	public Vector3 WishVelocity { get; set; }

	/// <summary>
	/// Are we on the ground?
	/// </summary>
	public bool IsGrounded { get; set; }

	/// <summary>
	/// How quick do we wish to go (normalized)
	/// </summary>
	public Vector3 WishMove { get; set; }

	/// <summary>
	/// How much friction to apply to the aim eg if zooming
	/// </summary>
	public float AimDampening { get; set; } = 1.0f;

	/// <summary>
	/// An accessor to get the camera controller's aim ray.
	/// </summary>
	public Ray AimRay => CameraController.AimRay;

	private float _smoothEyeHeight;

	// Keep the first-person body hidden until the camera clears it when standing up.
	public bool HideFirstPersonBodyForStance => IsProne || _smoothEyeHeight < -18f;
	private Vector3 _previousVelocity;
	private bool _isTouchingLadder;
	private Vector3 _ladderNormal;

	[Sync] private float _eyeHeightOffset { get; set; }

	private void UpdateEyes()
	{
		// Run always so CrouchNavMeshLink makes bots to crouch.
		// if ( IsLocallyControlled )
		{
			var eyeHeightOffset = GetEyeHeightOffset();

			var target = eyeHeightOffset;
			var trace = TraceBBox( WorldPosition, WorldPosition, 0, 10f );
			if ( trace.Hit && target > _smoothEyeHeight )
			{
				// We hit something, that means we can't increase our eye height because something's in the way.
				eyeHeightOffset = _smoothEyeHeight;
				IsCrouching = true;
			}
			else
			{
				eyeHeightOffset = target;
			}

			_eyeHeightOffset = eyeHeightOffset;
		}

		if ( PlayerBoxCollider.IsValid() )
		{
			// Bit shit, but it works
			var stanceHeight = Height + _smoothEyeHeight;
			PlayerBoxCollider.Center = new( 0, 0, stanceHeight * 0.5f );
			PlayerBoxCollider.Scale = new( 32, 32, stanceHeight );
		}
	}

	TimeUntil TimeUntilAccelerationRecovered = 0;
	float AccelerationAddedScale = 0;

	private void ApplyAcceleration()
	{
		var relative = TimeUntilAccelerationRecovered.Fraction.Clamp( 0, 1 );
		var acceleration = GetAcceleration();

		acceleration *= (relative + AccelerationAddedScale).Clamp( 0, 1 );

		CharacterController.Acceleration = acceleration;
	}

	private void OnUpdateMovement()
	{
		UpdateFallKnockdown();
		UpdateMantleBlend();

		var cc = CharacterController;
		CurrentHoldType = CurrentEquipment.IsValid() ? CurrentEquipment.GetHoldType() : AnimationHelper.HoldTypes.None;

		// Sync velocity and ground state for remote player animations
		if ( IsLocallyControlled && cc.IsValid() )
		{
			SyncedVelocity = cc.Velocity;
			SyncedIsGrounded = cc.IsOnGround;
		}

		if ( !IsLocallyControlled )
		{
			_smoothEyeAngles = Angles.Lerp( _smoothEyeAngles, _rawEyeAngles, Time.Delta / Scene.NetworkRate );
		}

		// Eye input
		if ( IsPossessed && cc.IsValid() )
		{
			if ( IsLocallyControlled && HealthComponent.State == LifeState.Alive )
			{
				EyeAngles += Input.AnalogLook * AimDampening;
				EyeAngles = EyeAngles.WithPitch( EyeAngles.pitch.Clamp( -90, 90 ) );
			}

			CameraController.UpdateFromEyes( _smoothEyeHeight );
		}

		if ( Body.IsValid() )
		{
			WorldRotation = Rotation.From( 0, EyeAngles.yaw, 0 );
			Body.UpdateRotation( Rotation.FromYaw( EyeAngles.yaw ) );

			// Use synced data for remote players, local data for the owner
			var velocityForAnimation = ( IsLocallyControlled && cc.IsValid() ) ? cc.Velocity : SyncedVelocity;
			var isGroundedForAnimation = ( IsLocallyControlled && cc.IsValid() ) ? IsGrounded : SyncedIsGrounded;

			foreach ( var helper in Body.AnimationHelpers )
			{
				if ( !helper.IsValid() ) continue;

				helper.WithVelocity( velocityForAnimation );
				helper.WithWishVelocity( WishVelocity );
				helper.IsGrounded = isGroundedForAnimation;
				helper.WithLook( EyeAngles.Forward );
				helper.MoveStyle = AnimationHelper.MoveStyles.Run;
				helper.DuckLevel = (MathF.Abs( _smoothEyeHeight ) / 32.0f).Clamp( 0f, 1f );
				helper.HoldType = CurrentHoldType;
				helper.Handedness = CurrentEquipment.IsValid() ? CurrentEquipment.GetHandedness() : AnimationHelper.Hand.Both;
			}
		}

		AimDampening = 1.0f;
	}

	private float GetMaxAcceleration()
	{
		if ( !CharacterController.IsOnGround ) return Global.AirMaxAcceleration;
		return Global.MaxAcceleration;
	}

	private void ApplyMovement()
	{
		var cc = CharacterController;

		CheckLadder();

		var gravity = Global.Gravity;

		if ( _isTouchingLadder )
		{
			LadderMove();
			return;
		}

		if ( cc.IsOnGround )
		{
			cc.Velocity = cc.Velocity.WithZ( 0 );
			cc.Accelerate( WishVelocity );
		}
		else
		{
			if ( !IsNoclipping )
			{
				cc.Velocity -= gravity * Time.Delta * 0.5f;
			}
			cc.Accelerate( WishVelocity.ClampLength( GetMaxAcceleration() ) );
		}

		if ( !cc.IsOnGround )
		{
			if ( !IsNoclipping )
			{
				cc.Velocity -= gravity * Time.Delta * 0.5f;
			}
		}
		else
		{
			cc.Velocity = cc.Velocity.WithZ( 0 );
		}

		if ( IsNoclipping )
		{
			var vertical = 0f;
			if ( Input.Down( "Jump" ) ) vertical = 1f;
			if ( Input.Down( "Duck" ) ) vertical = -1f;

			cc.IsOnGround = false;
			cc.Velocity = WishMove.Normal * EyeAngles.ToRotation() * NoclipSpeed;
			cc.Velocity += Vector3.Up * vertical * NoclipSpeed;
		}

		// The standing stop-speed floor can erase an entire slow crawl each tick.
		if ( IsProne ) cc.ApplyFriction( GetFriction(), MathF.Max( GetWishSpeed(), 1f ) );
		else cc.ApplyFriction( GetFriction() );
		cc.Move();
	}

	private bool WantsToggleSprint { get; set; }

	private bool HasSprintMovement => WishMove.x > 0.2f || (MathF.Abs( WishMove.y ) > 0.2f && WishMove.x >= 0f);
	private bool CanSprint => !IsMantling && !IsFallKnockedDown && !IsSlowWalking && !IsProne && !IsGettingUp && !HasEquipmentTag( "no_sprint" );

	private bool GetWantsToSprint()
	{
		// Shooting breaks the sprint. Without this, holding fire while running is simply swallowed by
		// the no_shooting tag and you stay stuck in the run animation until you let go of Run.
		if ( Input.Down( "Attack1" ) && !HasEquipmentTag( "aiming" ) )
		{
			WantsToggleSprint = false;
			return false;
		}

		if ( GameSettingsSystem.Current.ToggleSprint )
		{
			if ( Input.Pressed( "Run" ) )
			{
				WantsToggleSprint = !WantsToggleSprint;
			}

			if ( !CanSprint )
			{
				WantsToggleSprint = false;
			}

			return WantsToggleSprint && CanSprint && HasSprintMovement;
		}

		WantsToggleSprint = false;
		return Input.Down( "Run" ) && CanSprint && HasSprintMovement;
	}
	TimeSince TimeSinceSprintChanged { get; set; } = 100;

	private void OnSprintChanged( bool before, bool after )
	{
		TimeSinceSprintChanged = 0;
	}
	public bool HasEquipmentTag( string flag )
	{
		return CurrentEquipment.IsValid() && CurrentEquipment.HasTag( flag );
	}

	private void BuildInput()
	{
		bool wasSprinting = IsSprinting;

		IsSlowWalking = !IsFallKnockedDown && Input.Down( "Walk" );
		IsSprinting = GetWantsToSprint();

		if ( wasSprinting != IsSprinting )
		{
			OnSprintChanged( wasSprinting, IsSprinting );
		}

		if ( IsFallKnockedDown )
		{
			IsProne = true;
			IsCrouching = false;
			IsUsing = false;
			return;
		}

		// Prone toggles rather than being held, and jumping gets you back on your feet. Both cost prone stamina.
		var downed = ZombiesPlayerState.For( this ) is { IsDowned: true };
		if ( Input.Pressed( "Prone" ) && !IsNoclipping && !downed )
			ToggleProne();

		// A jump press that gets you up is spent on that: you can't jump off the floor from lying flat.
		var gotUpWithJump = IsProne && Input.Pressed( "Jump" ) && !downed;
		if ( gotUpWithJump )
			ToggleProne();

		// Zombies: downed players are stuck on the floor until revived, and get up when they are.
		if ( downed )
		{
			IsProne = true;
			IsSprinting = false;
		}
		else if ( _wasDowned )
		{
			IsProne = false;
		}
		_wasDowned = downed;

		IsCrouching = Input.Down( "Duck" ) && !IsNoclipping;
		IsUsing = Input.Down( "Use" );
		
		if ( Input.Pressed( "Scorestreak" ) )
		{
			if ( Client.IsValid() )
			{
				var score = Client.GetComponent<Facepunch.UI.PlayerScore>();
				if ( score.IsValid() )
				{
					score.CallInUAV();
				}
			}
		}

		// Check if our current weapon has the planting tag and if so force us to crouch.
		var currentWeapon = CurrentEquipment;
		if ( currentWeapon.IsValid() && currentWeapon.Tags.Has( "planting" ) )
			IsCrouching = true;

		if ( Input.Pressed( "Noclip" ) && Game.IsEditor )
		{
			IsNoclipping = !IsNoclipping;
		}

		if ( WishMove.LengthSquared > 0.01f || Input.Down( "Attack1" ) )
		{
			TimeSinceLastInput = 0f;
		}

		// Jump fatigue only wears off with your feet on the ground.
		if ( CharacterController.IsOnGround )
			JumpFatigue = MathF.Max( 0f, JumpFatigue - JumpFatigueRecovery * Time.Delta );

		if ( ProneFatigue > 0f )
			ProneFatigue = MathF.Max( 0f, ProneFatigue - ProneFatigueRecovery * Time.Delta );

		if ( CharacterController.IsOnGround && !IsFrozen && !gotUpWithJump )
		{
			// A ledge in front of you is climbed, or a low wall vaulted, rather than jumped at.
			var mantled = Input.Pressed( "Jump" ) && TryStartMantle( airborne: false );

			var bhop = Global.BunnyHopping;
			if ( !mantled && (bhop ? Input.Down( "Jump" ) : Input.Pressed( "Jump" )) )
				Jump();
		}
		else if ( !CharacterController.IsOnGround && !IsFrozen && Input.Down( "Jump" ) )
		{
			// Holding Jump in the air catches a ledge the jump brings into reach.
			TryStartMantle( airborne: true );
		}
	}

	/// <summary>Jump off the ground, as high as <see cref="JumpFatigue"/> allows.</summary>
	internal void Jump()
	{
		CharacterController.Punch( Vector3.Up * Global.JumpPower * (1f - JumpFatigue) );
		JumpFatigue = MathF.Min( JumpFatigue + JumpFatigueCost * (1f - JumpFatigue), MaxJumpFatigue );
		BroadcastPlayerJumped();
	}

	/// <summary>
	/// Jump stamina, like CS2's: each jump takes this share of the jump speed you have left, so jumping again as soon as
	/// you land goes lower every time (100%, 85%, 72%, 61% of the speed), down to <see cref="MaxJumpFatigue"/>.
	/// </summary>
	public const float JumpFatigueCost = 0.15f;

	/// <summary>Fatigue worn off per second on the ground: a full jump again ~0.4 s after one jump, ~1.2 s after many.</summary>
	public const float JumpFatigueRecovery = 0.375f;

	/// <summary>The most a jump loses: 45% of its speed, which leaves about a third of a full jump's height.</summary>
	public const float MaxJumpFatigue = 0.45f;

	/// <summary>How much of the next jump's speed is gone (see <see cref="JumpFatigueCost"/>). Only the owner moves the pawn.</summary>
	public float JumpFatigue { get; private set; }

	/// <summary>Lie down or get up, as the Prone key does, paying for it in prone stamina (<see cref="ProneFatigue"/>).</summary>
	internal void ToggleProne()
	{
		IsProne = !IsProne;
		ProneFatigue = MathF.Min( ProneFatigue + (IsProne ? ProneDropCost : ProneRiseCost), 1f );
	}

	/// <summary>
	/// Prone stamina, like CS's crouch speed: getting down flat and getting up each take something out of you, getting up
	/// more, since you push yourself off the floor. A drop and a get-up now and then cost nothing you'd notice, but going
	/// up and down again and again slows every stance change (<see cref="StanceChangeRate"/>), getting up most, until it
	/// wears off. Spammed, it bogs down after two or three drops.
	/// </summary>
	public const float ProneDropCost = 0.2f;

	/// <summary>What getting up from prone costs (see <see cref="ProneDropCost"/>).</summary>
	public const float ProneRiseCost = 0.3f;

	/// <summary>Prone fatigue worn off per second: from exhausted back to full speed in ~3 s, and to none in 5 s.</summary>
	public const float ProneFatigueRecovery = 0.2f;

	/// <summary>Prone fatigue up to this doesn't slow anything, so an odd drop and get-up don't.</summary>
	public const float ProneFatigueFree = 0.35f;

	/// <summary>Exhausted, getting down goes at 30% of the speed: flat in ~1 s instead of 0.3 s.</summary>
	public const float ProneDropSlowdown = 0.7f;

	/// <summary>
	/// Exhausted, getting up goes at 15% of the speed: past crouch height in ~0.6 s and fully up in ~2 s, instead of 0.1 s
	/// and 0.3 s.
	/// </summary>
	public const float ProneRiseSlowdown = 0.85f;

	/// <summary>
	/// How tired going prone and getting up have made you, 0 to 1 (see <see cref="ProneDropCost"/>). The owner sets it, and
	/// every machine slows the stance change by it, so everyone sees the same body height.
	/// </summary>
	[Sync] public float ProneFatigue { get; private set; }

	/// <summary>
	/// How fast the eyes, and with them the body's height, follow a stance change, as a lerp rate per second: 10 fresh,
	/// less once <see cref="ProneFatigue"/> is past <see cref="ProneFatigueFree"/>.
	/// </summary>
	private float StanceChangeRate( bool rising )
	{
		var tired = ((ProneFatigue - ProneFatigueFree) / (1f - ProneFatigueFree)).Clamp( 0f, 1f );
		return 10f * (1f - tired * (rising ? ProneRiseSlowdown : ProneDropSlowdown));
	}

	/// <summary>Up from prone but not yet at crouch height (-16): you can't run off the floor before you're up.</summary>
	private bool IsGettingUp => !IsProne && _smoothEyeHeight < -17f;

	public SceneTraceResult TraceBBox( Vector3 start, Vector3 end, float liftFeet = 0.0f, float liftHead = 0.0f )
	{
		var bbox = CharacterController.BoundingBox;
		var mins = bbox.Mins;
		var maxs = bbox.Maxs;

		if ( liftFeet > 0 )
		{
			start += Vector3.Up * liftFeet;
			maxs = maxs.WithZ( maxs.z - liftFeet );
		}

		if ( liftHead > 0 )
		{
			end += Vector3.Up * liftHead;
		}

		var tr = Scene.Trace.Ray( start, end )
					.Size( mins, maxs )
					.WithoutTags( CharacterController.IgnoreLayers )
					.IgnoreGameObjectHierarchy( GameObject.Root )
					.Run();
		return tr;
	}

	/// <summary>
	/// A network message that lets other users that we've triggered a jump.
	/// </summary>
	[Rpc.Broadcast]
	public void BroadcastPlayerJumped()
	{
		foreach ( var helper in Body.AnimationHelpers )
		{
			if ( !helper.IsValid() ) continue;
			helper.TriggerJump();
		}

		OnJump?.Invoke();
	}

	public TimeSince TimeSinceGroundedChanged { get; private set; }

	private void GroundedChanged( bool wasOnGround, bool isOnGround )
	{
		if ( !IsLocallyControlled )
			return;

		TimeSinceGroundedChanged = 0;

		if ( !wasOnGround && isOnGround && Global.EnableFallDamage && !IsNoclipping )
		{
			var minimumVelocity = MinimumFallVelocity;
			var vel = MathF.Abs( _previousVelocity.z );

			if ( vel >= FallKnockdownVelocity )
				StartFallKnockdown();

			// A vault's landing is heard even off a wall too low for a fall's sound.
			if ( vel > MinimumFallSoundVelocity || _vaultLanding )
			{
				PlayFallSound( vel );
			}
			_vaultLanding = false;
			if ( vel > minimumVelocity )
			{
				var velPastAmount = vel - minimumVelocity;

				TimeUntilAccelerationRecovered = 1f;
				AccelerationAddedScale = 0f;

				using ( Rpc.FilterInclude( Connection.Host ) )
				{
					TakeFallDamage( velPastAmount * FallDamageScale );
				}
			}
		}
	}

	private void StartFallKnockdown()
	{
		if ( IsFallKnockedDown || IsProne || HealthComponent.State != LifeState.Alive )
			return;

		if ( ZombiesPlayerState.For( this ) is { IsDowned: true } )
			return;

		IsFallKnockedDown = true;
		TimeSinceFallKnockdown = 0f;
		IsProne = true;
		IsSprinting = false;

		if ( CurrentEquipment.IsValid() )
		{
			foreach ( var aimable in CurrentEquipment.Components.GetAll<Aimable>( FindMode.EverythingInSelfAndDescendants ) )
				if ( aimable.IsValid() ) aimable.CancelAim();
		}
	}

	private void UpdateFallKnockdown()
	{
		if ( !IsFallKnockedDown || !IsLocallyControlled )
			return;

		if ( HealthComponent.State != LifeState.Alive || TimeSinceFallKnockdown >= FallKnockdownDuration )
		{
			IsFallKnockedDown = false;
			IsProne = false;
			return;
		}

		IsProne = true;
	}

	[Property, Group( "Effects" )] public SoundEvent LandSound { get; set; }

	/// <summary>
	/// The landing's speed (units a second) that its sounds are made for: a jump's, from ~50 units up.
	/// </summary>
	private const float LandingSoundSpeed = 300f;

	/// <summary>
	/// Both boots coming down on the floor underfoot (<see cref="WorldSounds.Landing"/>, else <see cref="LandSound"/>),
	/// louder the faster they land: the force through the floor goes with the speed.
	/// </summary>
	[Rpc.Broadcast]
	private void PlayFallSound( float speed )
	{
		var tr = Scene.Trace.Ray( WorldPosition + Vector3.Up * 20, WorldPosition + Vector3.Down * 20 )
			.IgnoreGameObjectHierarchy( GameObject )
			.WithoutTags( "corpse" )
			.Run();

		var sound = (tr.Hit ? WorldSounds.Landing( WorldSounds.SurfaceAt( tr ) ) : null) ?? LandSound;
		var snd = Sound.Play( sound, WorldPosition );
		if ( !snd.IsValid() ) return;

		snd.Volume *= (speed / LandingSoundSpeed).Clamp( 0.6f, 2f );
		snd.SpacialBlend = IsViewer ? 0 : snd.SpacialBlend;
	}

	[Rpc.Broadcast]
	private void TakeFallDamage( float damage )
	{
		GameObject.TakeDamage( new DamageInfo( this, damage, null, WorldPosition, Flags: DamageFlags.FallDamage ) );
	}

	private void CheckLadder()
	{
		var cc = CharacterController;
		var wishvel = new Vector3( WishMove.x.Clamp( -1f, 1f ), WishMove.y.Clamp( -1f, 1f ), 0 );
		wishvel *= EyeAngles.WithPitch( 0 ).ToRotation();
		wishvel = wishvel.Normal;

		if ( _isTouchingLadder )
		{
			if ( Input.Pressed( "jump" ) )
			{
				cc.Velocity = _ladderNormal * 100.0f;
				_isTouchingLadder = false;
				return;

			}
			else if ( cc.GroundObject != null && _ladderNormal.Dot( wishvel ) > 0 )
			{
				_isTouchingLadder = false;
				return;
			}
		}

		const float ladderDistance = 1.0f;
		var start = WorldPosition;
		Vector3 end = start + (_isTouchingLadder ? (_ladderNormal * -1.0f) : wishvel) * ladderDistance;

		var pm = Scene.Trace.Ray( start, end )
					.Size( cc.BoundingBox.Mins, cc.BoundingBox.Maxs )
					.WithTag( "ladder" )
					.HitTriggers()
					.IgnoreGameObjectHierarchy( GameObject )
					.Run();

		_isTouchingLadder = false;

		if ( pm.Hit )
		{
			_isTouchingLadder = true;
			_ladderNormal = pm.Normal;
		}
	}

	private void LadderMove()
	{
		var cc = CharacterController;
		cc.IsOnGround = false;

		var velocity = WishVelocity;
		float normalDot = velocity.Dot( _ladderNormal );
		var cross = _ladderNormal * normalDot;
		cc.Velocity = (velocity - cross) + (-normalDot * _ladderNormal.Cross( Vector3.Up.Cross( _ladderNormal ).Normal ));
		cc.Move();
	}

	void IGameEventHandler<WeaponShotEvent>.OnGameEvent( WeaponShotEvent ev )
	{
		if ( !ev.Equipment.IsValid() || ev.Equipment.Owner != this )
			return;

		TimeSinceLastInput = 0;
		if ( Networking.IsHost )
			Scene.Dispatch( new PlayerFiredWhileSpawnedEvent( this ) );
		else if ( TimeSinceLastRespawn < 10f )
			ReportSpawnProtectionShot();
	}

	[Rpc.Host]
	private void ReportSpawnProtectionShot()
	{
		if ( !Client.IsValid() || Rpc.Caller != Client.Connection || TimeSinceLastRespawn >= 10f )
			return;

		Scene.Dispatch( new PlayerFiredWhileSpawnedEvent( this ) );
	}

	private void BuildWishInput()
	{
		WishMove = 0f;

		if ( IsFrozen || IsFallKnockedDown )
			return;

		WishMove += Input.AnalogMove;

		if ( DevCommands.ForceMove != 0f && IsLocallyControlled )
			WishMove += Vector3.Forward * DevCommands.ForceMove;
	}

	private void BuildWishVelocity()
	{
		WishVelocity = 0f;

		var rot = EyeAngles.WithPitch( 0f ).ToRotation();

		if ( WishMove.Length > 1f )
			WishMove = WishMove.Normal;

		var wishDirection = WishMove * rot;
		wishDirection = wishDirection.WithZ( 0 );
		WishVelocity = wishDirection * GetWishSpeed();
	}

	/// <summary>
	/// Get the current friction.
	/// </summary>
	/// <returns></returns>
	// TODO: expose to global
	private float GetFriction()
	{
		if ( !CharacterController.IsOnGround ) return 0.1f;
		if ( IsProne ) return Global.CrouchingFriction;
		if ( IsSlowWalking ) return Global.SlowWalkFriction;
		if ( IsCrouching ) return Global.CrouchingFriction;
		if ( IsSprinting ) return Global.SprintingFriction;
		return Global.WalkFriction;
	}

	private float GetAcceleration()
	{
		if ( !CharacterController.IsOnGround ) return Global.AirAcceleration;
		else if ( IsProne ) return Global.CrouchingAcceleration;
		else if ( IsSlowWalking ) return Global.SlowWalkAcceleration;
		else if ( IsCrouching ) return Global.CrouchingAcceleration;
		else if ( IsSprinting ) return Global.SprintingAcceleration;

		return Global.BaseAcceleration;
	}

	float GetEyeHeightOffset()
	{
		// Tucked going over a ledge (PlayerPawn.Mantle.cs).
		if ( IsMantling && HealthComponent.State == LifeState.Alive ) return MantleEyeOffset;
		if ( IsProne ) return -40f;
		if ( IsCrouching ) return -16f;
		if ( HealthComponent.State == LifeState.Dead ) return -48f;
		return 0f;
	}

	private float GetSpeedPenalty()
	{
		var wpn = CurrentEquipment;
		if ( !wpn.IsValid() ) return 0;
		return wpn.SpeedPenalty;
	}

	public float GetWishSpeed()
	{
		float speed = 0f;
		if ( IsProne )
		{
			speed = Global.ProneSpeed;
		}
		else if ( IsSlowWalking )
		{
			speed = Global.SlowWalkSpeed;
		}
		else if ( IsCrouching || IsGettingUp )
		{
			speed = Global.CrouchingSpeed;
		}
		else if ( IsSprinting )
		{
			speed = Global.SprintingSpeed - (GetSpeedPenalty() * 0.5f);
		}
		else
		{
			speed = Global.WalkSpeed - GetSpeedPenalty();
		}

		// A heavy gun slows every gait by the same fraction, and so do heavy parts on it.
		if ( CurrentEquipment.IsValid() )
			speed *= 1f - (CurrentEquipment.WeightSlowdown + CurrentEquipment.AttachmentWeightSlowdown);

		// A shot leg or foot (hardcore), or a landing hard enough to hurt.
		speed *= HealthComponent.WoundSpeedScale;

		if ( Components.TryGet<PlayerPerks>( out var perks, FindMode.EnabledInSelf ) && perks.HasPerk( "lightweight" ) )
		{
			speed *= 1.07f; // 7% increase
		}

		// Zombies: Fleet Foot, and crawling while downed.
		speed *= ZombiesPlayerState.MoveSpeedScale( this );

		// Unsteady on your feet for a few seconds after a flashbang's blast.
		speed *= FlashbangEffect.MoveSpeedScale( this );

		return speed;
	}

	private void DebugUpdate()
	{
		DebugText.Update();
		DebugText.Write( $"Player", Color.White, 20 );
		DebugText.Write( $"Velocity: {CharacterController.Velocity}" );
		DebugText.Write( $"Speed: {CharacterController.Velocity.Length}" );
		DebugText.Spacer();
		DebugText.Write( $"Weapon Info", Color.White, 20 );
		DebugText.Write( $"Spread: {Spread}" );
	}
}
