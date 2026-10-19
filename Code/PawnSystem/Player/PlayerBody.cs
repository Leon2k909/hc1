namespace Facepunch;

public partial class PlayerBody : Component
{
	[Property] public SkinnedModelRenderer Renderer { get; set; }
	[Property] public ModelPhysics Physics { get; set; }
	[Property] public PlayerPawn Player { get; set; }
	[Property] public GameObject FirstPersonBody { get; set; }
	[Property] public List<AnimationHelper> AnimationHelpers { get; set; } = new();

	public Vector3 DamageTakenPosition { get; set; }
	public Vector3 DamageTakenForce { get; set; }

	private bool IsFirstPerson;
	public bool IsRagdoll => Physics.Enabled;

	internal void SetRagdoll( bool ragdoll )
	{
		Physics.Enabled = ragdoll;
		Renderer.UseAnimGraph = !ragdoll;

		GameObject.Tags.Set( "ragdoll", ragdoll );

		if ( !ragdoll )
		{
			GameObject.LocalPosition = Vector3.Zero;
			GameObject.LocalRotation = Rotation.Identity;
		}

		SetFirstPersonView( !ragdoll );

		if ( ragdoll && DamageTakenForce.LengthSquared > 0f )
			ApplyRagdollImpulses( DamageTakenPosition, DamageTakenForce );

		Transform.ClearInterpolation();
	}

	internal void ApplyRagdollImpulses( Vector3 position, Vector3 force )
	{
		if ( !Physics.IsValid() || !Physics.PhysicsGroup.IsValid() )
			return;

		foreach ( var body in Physics.PhysicsGroup.Bodies )
		{
			body.ApplyImpulseAt( position, force );
		}
	}

	public void Refresh()
	{
		SetFirstPersonView( IsFirstPerson );
	}

	public void SetFirstPersonView( bool firstPerson )
	{
		IsFirstPerson = firstPerson;

		if ( Player.CurrentEquipment.IsValid() )
		{
			Player.CurrentEquipment.UpdateRenderMode();
		}

		UpdateFirstPersonBodyVisibility();
	}

	private void UpdateFirstPersonBodyVisibility()
	{
		if ( !FirstPersonBody.IsValid() ) return;
		// From the drone's camera the operator's own body is seen whole, so the legs-only copy would be a second one.
		FirstPersonBody.Enabled = IsFirstPerson && Player.IsValid() && !Player.HideFirstPersonBodyForStance
			&& !Player.IsPilotingDrone;

		// Only its legs are for seeing: the human model's face came into view when it leaned into a walk.
		if ( !_firstPersonUniform.IsValid() )
		{
			_firstPersonUniform = FirstPersonBody.GetComponent<MilitaryUniform>( true );
			_firstPersonUniform?.ShowLegsOnly();
		}
	}

	private MilitaryUniform _firstPersonUniform;
	private readonly ThirdPersonTabletPose _tabletPose = new();

	internal void ApplyTabletPose()
	{
		var station = Player?.CurrentEquipment?.WorldModel;
		if ( !Player.IsValid() || !Player.HealthComponent.IsValid() || Player.HealthComponent.State != LifeState.Alive
			|| !Renderer.IsValid() || !Renderer.UseAnimGraph || (Physics.IsValid() && Physics.Enabled)
			|| !station.IsValid() || !station.Active || !station.UseTabletPose ) return;
		_tabletPose.Apply( Renderer, station );
	}

	private readonly ThirdPersonSlidePose _slidePose = new();
	private readonly ThirdPersonSprintPose _sprintPose = new();
	private float _sprintPoseBlend;

	internal void ApplySprintPose()
	{
		var equipment = Player?.CurrentEquipment;
		var gun = equipment?.WorldModel;
		if ( !Player.IsValid() || !Player.HealthComponent.IsValid() || Player.HealthComponent.State != LifeState.Alive
			|| !Renderer.IsValid() || !Renderer.UseAnimGraph || (Physics.IsValid() && Physics.Enabled)
			|| !equipment.IsValid() || !gun.IsValid() || !gun.Active || gun.UseTabletPose
			|| equipment.GetHoldType() is not (AnimationHelper.HoldTypes.Rifle or AnimationHelper.HoldTypes.Shotgun)
			|| Player.IsProne || Player.IsCrouching || Player.IsFallKnockedDown || Player.IsMantling || Player.IsPipeClimbing || Player.SlideBlend > 0f
			|| equipment.Components.Get<Reloadable>( FindMode.EnabledInSelfAndDescendants )?.IsReloading == true )
		{
			_sprintPoseBlend = 0f;
			_sprintPose.Reset();
			return;
		}
		_sprintPoseBlend = ThirdPersonSprintPose.UpdateBlend( _sprintPoseBlend, Player.IsSprinting && !Player.HasEquipmentTag( "aiming" ), Time.Delta );
		// Migrated player prefabs keep their authored hand socket; using a bot's offset would leave an offset
		// on the weapon when the carry ends, and make it jump as the normal hand animation takes over.
		Transform? mount = MilitaryUniform.UsesHumanSkeleton( Renderer.Model ) && Player.HoldGameObject.IsValid()
			? Player.HoldGameObject.LocalTransform : null;
		_sprintPose.Apply( Renderer, gun, _sprintPoseBlend, handToWeaponOverride: mount );
	}

	/// <summary>A pistol is held out towards arm's length: its back 14 units in front of the eye (EyeOnGun's buttToEye).</summary>
	private const float PistolEyeBehindGrip = -14f;

	private readonly ThirdPersonPronePose _pronePose = new();
	private readonly ThirdPersonPronePose _firstPersonPronePose = new();
	private SkinnedModelRenderer _firstPersonRenderer;

	/// <summary>
	/// Lay the body out on the floor under the camera, and the first-person legs with it, so they can be seen lying
	/// there (PlayerPawn.Prone.cs). Only living, animated bodies: a ragdoll has its own pose.
	/// </summary>
	internal void ApplyPronePose()
	{
		if ( !Player.IsValid() || Player.ProneBlend <= 0f || !Player.HealthComponent.IsValid()
			|| Player.HealthComponent.State != LifeState.Alive ) return;

		var eye = Player.ProneEyeTarget;
		var ground = Player.WorldPosition.z;
		if ( Renderer.IsValid() && Renderer.UseAnimGraph && !(Physics.IsValid() && Physics.Enabled) )
		{
			_pronePose.Apply( Renderer, Player.ProneBlend, Player.SupineBlend, Player.ProneYaw, eye, ground,
				Player.ProneCrawlBlend, Player.ProneCrawlPhase );
			// A gun comes up to the eye, as a prone shooter holds it; the reload keeps its own hands.
			var equipment = Player.CurrentEquipment;
			var gun = equipment?.WorldModel;
			var hold = equipment.IsValid() ? equipment.GetHoldType() : AnimationHelper.HoldTypes.None;
			if ( gun.IsValid() && gun.Active && !gun.UseTabletPose
				&& hold is AnimationHelper.HoldTypes.Rifle or AnimationHelper.HoldTypes.Shotgun or AnimationHelper.HoldTypes.Pistol
				&& equipment.Components.Get<Reloadable>( FindMode.EnabledInSelfAndDescendants )?.IsReloading != true )
				_pronePose.ShoulderGun( Renderer, gun, eye, Player.EyeAngles.Forward, Player.ProneBlend,
					hold == AnimationHelper.HoldTypes.Pistol ? PistolEyeBehindGrip : LightweightCombatBot.ButtToEye );
		}

		if ( !FirstPersonBody.IsValid() || !FirstPersonBody.Active ) return;
		if ( !_firstPersonRenderer.IsValid() ) _firstPersonRenderer = FirstPersonBody.GetComponent<SkinnedModelRenderer>();
		if ( _firstPersonRenderer.IsValid() && _firstPersonRenderer.UseAnimGraph )
			_firstPersonPronePose.Apply( _firstPersonRenderer, Player.ProneBlend, Player.SupineBlend, Player.ProneYaw, eye, ground,
				Player.ProneCrawlBlend, Player.ProneCrawlPhase );
	}

	internal void ApplySlidePose()
	{
		if ( !Player.IsValid() || Player.SlideBlend <= 0f || !Player.HealthComponent.IsValid() || Player.HealthComponent.State != LifeState.Alive
			|| !Renderer.IsValid() || !Renderer.UseAnimGraph || (Physics.IsValid() && Physics.Enabled)
			|| Player.IsProne || Player.IsMantling || Player.IsPipeClimbing ) return;
		_slidePose.Apply( Renderer, Player.SlideBlend );
	}

	protected override void OnUpdate()
	{
		if ( !Player.IsValid() )
			return;

		if ( !Player.CameraController.IsValid() )
			return;

		var isWatchingThisPlayer = Client.Viewer.IsValid() && Client.Viewer.Pawn == Player;
		Tags.Set( "viewer", isWatchingThisPlayer && Player.CameraController.Mode == CameraMode.FirstPerson );
		UpdateFirstPersonBodyVisibility();
	}

	internal void UpdateRotation( Rotation rotation )
	{
		WorldRotation = rotation;
		FirstPersonBody.WorldRotation = rotation;
	}
}
